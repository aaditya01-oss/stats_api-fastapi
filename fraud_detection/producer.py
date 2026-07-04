"""
producer.py — Kafka transaction producer.

Simulates a payment processing system generating
credit card transactions in real time.

A Kafka producer:
  - Connects to the Kafka broker
  - Serializes data to JSON (bytes)
  - Publishes messages to a topic
  - Each message has a key (card_id) and value (transaction data)

The key matters — Kafka guarantees that all messages with
the same key go to the same partition. This means all
transactions from the same card are in order.
"""

import json
import time
import random
import uuid
import numpy as np
from datetime import datetime, timezone
from kafka import KafkaProducer




TOPIC = "transactions"
KAFKA_BOOTSTRAP = "localhost:9092"  # from your machine


def create_producer() -> KafkaProducer:
    """
    Creates a Kafka producer.

    value_serializer converts Python dicts to JSON bytes
    automatically before sending. Kafka only stores bytes —
    it has no concept of JSON or Python objects.
    """
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8"),
    )


def generate_transaction(fraud_probability: float = 0.08) -> dict:
    """
    Generates a single synthetic credit card transaction.
    """
    is_fraud_attempt = random.random() < fraud_probability
    now = datetime.now(timezone.utc)

    if is_fraud_attempt:
        return {
            "transaction_id": str(uuid.uuid4()),
            "card_id": f"card_{random.randint(1000, 9999)}",
            "amount": round(float(np.random.uniform(500, 5000)), 2),
            "hour": random.choice([1, 2, 3, 4]),
            "day_of_week": random.randint(0, 6),
            "merchant_category": random.randint(0, 9),
            "distance_from_home": round(float(np.random.uniform(200, 2000)), 1),
            "timestamp": now.isoformat(),
            "true_label": "FRAUD",
        }
    else:
        return {
            "transaction_id": str(uuid.uuid4()),
            "card_id": f"card_{random.randint(1000, 9999)}",
            "amount": round(float(np.random.lognormal(mean=3.5, sigma=0.8)), 2),
            "hour": random.randint(8, 21),
            "day_of_week": random.randint(0, 6),
            "merchant_category": random.randint(0, 9),
            "distance_from_home": round(float(np.random.exponential(scale=5)), 1),
            "timestamp": now.isoformat(),
            "true_label": "NORMAL",
        }

def run_producer(transactions_per_second: float = 2.0) -> None:
    """
    Continuously generates and publishes transactions.

    transactions_per_second: controls how fast we produce.
    2.0 = 2 transactions per second = realistic payment volume.
    """
    producer = create_producer()
    interval = 1.0 / transactions_per_second
    count = 0

    print(f"Producer started. Publishing to topic '{TOPIC}'...")
    print(f"Rate: {transactions_per_second} transactions/second")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            transaction = generate_transaction()
            producer.send(
                topic=TOPIC,
                key=transaction["card_id"],
                value=transaction,
            )
            count += 1
            print(f"[{count:04d}] Sent: {transaction['card_id']} "
                  f"${transaction['amount']:>8.2f} "
                  f"{'🚨 FRAUD ATTEMPT' if transaction['true_label'] == 'FRAUD' else '✓ normal'}")
            time.sleep(interval)

    except KeyboardInterrupt:
        print(f"\nProducer stopped. Sent {count} transactions.")
        producer.flush()  # send any buffered messages before stopping
        producer.close()


if __name__ == "__main__":
    run_producer()