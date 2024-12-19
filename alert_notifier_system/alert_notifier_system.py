from confluent_kafka import Consumer, KafkaException
import os
import json
from notifier import send_email

consumer_config = {
    'bootstrap.servers': os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
    'group.id': 'alert_notifier_group',
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': True
}

consumer = Consumer(consumer_config)
consumer.subscribe(['to-notifier'])

try:
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print(f"E' stato rilevato un errore dal consumatore: {msg.error()}")
            continue

        data = json.loads(msg.value().decode('utf-8'))
        email = data['email']
        ticker = data['ticker']
        ThresholdValue = data['threshold_value']
        ChoosenThreshold = data['condition']
        value_ticker_registered = data['value_ticker']

        send_email(email, ticker, ThresholdValue, ChoosenThreshold, value_ticker_registered)
except KeyboardInterrupt:
    print("Processo interrotto dall'utente")
finally:
    consumer.close()