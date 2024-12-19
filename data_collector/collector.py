import yfinance as yf
import time
import logging
import os
from confluent_kafka import Producer
from common.database import SessionLocal
from common.models import FinancialData, User
from circuit_breaker import CircuitBreaker

logging.getLogger('yfinance').setLevel(logging.CRITICAL)

KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

def get_stock_price(ticker):
    """
    Recupera il prezzo corrente del ticker utilizzando yfinance.
    """
    data = yf.Ticker(ticker)
    hist = data.history(period="1d")
    if not hist.empty:
        return float(hist['Close'][0])
    else:
        raise ValueError(f"Nessun dato trovato per il ticker: {ticker}")

def delivery_report(err, msg):
    """
    Callback eseguito alla consegna del messaggio Kafka.
    """
    if err is not None:
        print(f"Errore nell'invio del messaggio a Kafka: {err}")
    else:
        print(f"Messaggio inviato a {msg.topic()} offset {msg.offset()}")

def main():
    circuit_breaker = CircuitBreaker()
    producer = Producer({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})

    while True:
        print("Avvio ciclo di raccolta dati")
        with SessionLocal() as session:
            
            tickers = session.query(User.ticker).distinct().all()
            tickers = [t[0] for t in tickers]

            for ticker in tickers:
                try:
                    
                    price = circuit_breaker.call(get_stock_price, ticker)
                    price = float(price)
                   
                    financial_data = FinancialData(
                        ticker=ticker,
                        value=price
                    )
                    session.add(financial_data)
                    session.commit()
                    print(f"Dato salvato per ticker {ticker}: {price}")
                except Exception as e:
                    print(f"Errore nel recupero dei dati per ticker {ticker}: {e}")

       
        msg_value = "Update completed"
        producer.produce('to-alert-system', key='update', value=msg_value.encode('utf-8'), callback=delivery_report)
        producer.flush()  

        print("Ciclo di raccolta dati completato, attesa 3 minuti")
        time.sleep(180)

if __name__ == '__main__':
    main()