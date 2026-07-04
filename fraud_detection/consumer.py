"""
consumer.py — Real-time fraud detection consumer.

A Kafka consumer:
  - Subscribes to one or more topics
  - Polls for new messages continuously
  - Processes each message as it arrives
  - Commits offsets (marks messages as processed)

Key concept — consumer offset:
  Kafka stores every message permanently.
  Your consumer tracks its "offset" — how far it has read.
  If the consumer crashes and restarts, it resumes from
  the last committed offset. No messages lost, no duplicates.
"""

import json
import os
import psycopg2
import mlflow
from datetime import datetime
from kafka import KafkaConsumer
from dotenv import load_dotenv
from fraud_detection.model import FraudDetectionModel

# Load .env file FIRST before anything else reads environment variables
load_dotenv()

# Debug — remove after confirming it works
print("POSTGRES_HOST:", os.getenv("POSTGRES_HOST", "NOT SET"))
print("POSTGRES_PASSWORD:", os.getenv("POSTGRES_PASSWORD", "NOT SET"))


TOPIC = "transactions"
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        database=os.getenv("POSTGRES_DB", "fraud_db"),
        user=os.getenv("POSTGRES_USER", "fraud"),
        password=os.getenv("POSTGRES_PASSWORD", "fraud"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
    )


def setup_database() -> None:
    """Create the fraud results table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fraud_detections (
            id                  SERIAL PRIMARY KEY,
            transaction_id      VARCHAR(50) UNIQUE,
            card_id             VARCHAR(20),
            amount              FLOAT,
            risk_score          FLOAT,
            is_fraud            BOOLEAN,
            decision            VARCHAR(10),
            true_label          VARCHAR(10),
            correct_prediction  BOOLEAN,
            processed_at        TIMESTAMP DEFAULT NOW()
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()
    print("Database table ready.")


def save_result(result: dict) -> None:
    """Persist a fraud detection result to PostgreSQL."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO fraud_detections
            (transaction_id, card_id, amount, risk_score,
             is_fraud, decision, true_label, correct_prediction)
        VALUES
            (%(transaction_id)s, %(card_id)s, %(amount)s, %(risk_score)s,
             %(is_fraud)s, %(decision)s, %(true_label)s, %(correct_prediction)s)
        ON CONFLICT (transaction_id) DO NOTHING;
    """, result)
    conn.commit()
    cursor.close()
    conn.close()


def run_consumer() -> None:
    """
    Main consumer loop — reads transactions from Kafka
    and scores them in real time.
    """
    # Train the model once before starting
    model = FraudDetectionModel()
    model.train()

    # Set up database
    setup_database()

    # Set up MLflow
    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment("fraud_detection_stream")

    # Create the Kafka consumer
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="latest",  # start from new messages
        group_id="fraud_detector_v1",
        # group_id enables consumer groups — multiple consumers
        # can share a topic's partitions for parallel processing
    )

    print(f"Consumer started. Listening to topic '{TOPIC}'...")
    print("Waiting for transactions...\n")

    processed = 0
    fraud_count = 0
    correct = 0

    with mlflow.start_run(run_name="fraud_detection_stream"):
        mlflow.log_param("model", "IsolationForest")
        mlflow.log_param("contamination", 0.05)

        try:
            for message in consumer:
                transaction = message.value

                # Score the transaction
                result = model.score_transaction(transaction)

                # Was our prediction correct?
                result["correct_prediction"] = (
                    result["decision"] == transaction["true_label"]
                )

                # Save to database
                save_result(result)

                # Update counters
                processed += 1
                if result["is_fraud"]:
                    fraud_count += 1
                if result["correct_prediction"]:
                    correct += 1

                # Log metrics to MLflow every 50 transactions
                if processed % 50 == 0:
                    accuracy = correct / processed
                    fraud_rate = fraud_count / processed
                    mlflow.log_metric("accuracy", accuracy, step=processed)
                    mlflow.log_metric("fraud_rate", fraud_rate, step=processed)
                    print(f"\n[Stats after {processed} transactions]")
                    print(f"  Accuracy:   {accuracy:.2%}")
                    print(f"  Fraud rate: {fraud_rate:.2%}")

                # Print result
                icon = "🚨" if result["is_fraud"] else "✓"
                correct_icon = "✅" if result["correct_prediction"] else "❌"
                print(
                    f"{icon} {result['card_id']} "
                    f"${result['amount']:>8.2f} "
                    f"risk={result['risk_score']:.3f} "
                    f"{result['decision']:<6} "
                    f"{correct_icon}"
                )

        except KeyboardInterrupt:
            print(f"\nConsumer stopped.")
            print(f"Processed: {processed} transactions")
            print(f"Fraud detected: {fraud_count}")
            print(f"Final accuracy: {correct/processed:.2%}" if processed else "")
            consumer.close()


if __name__ == "__main__":
    run_consumer()