"""
model.py — Fraud detection model.

Isolation Forest is perfect for fraud detection because:
- You don't need labelled fraud examples to train it
- It learns what "normal" looks like and flags outliers
- Fast enough to run in real time on a stream

How Isolation Forest works:
  It randomly partitions data by picking a feature and a split point.
  Anomalies (fraud) are isolated quickly — they need fewer splits.
  Normal points need many splits to isolate.
  The anomaly score = how few splits were needed.
"""

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


class FraudDetectionModel:
    """
    Real-time fraud detector using Isolation Forest.
    Train once on normal transactions, then score each new
    transaction as it arrives from the Kafka stream.
    """

    def __init__(self, contamination: float = 0.05) -> None:
        """
        Args:
            contamination: Expected fraction of fraudulent transactions.
                          0.05 = we expect ~5% of transactions to be fraud.
                          This calibrates the decision boundary.
        """
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100,
        )
        self.scaler = StandardScaler()
        self.is_trained = False

    def generate_training_data(self, n_samples: int = 5000) -> np.ndarray:
        """
        Generates synthetic normal transaction data for training.

        In production: pull historical non-fraud transactions
        from your database.

        Features:
          - amount:       transaction amount in dollars
          - hour:         hour of day (0-23)
          - day_of_week:  0=Monday, 6=Sunday
          - merchant_cat: merchant category code (simplified 0-9)
          - distance:     distance from home location in km
        """
        np.random.seed(42)
        return np.column_stack([
            np.random.lognormal(mean=3.5, sigma=1.2, size=n_samples),  # amount
            np.random.randint(8, 22, size=n_samples),                   # hour (business hours)
            np.random.randint(0, 7, size=n_samples),                    # day of week
            np.random.randint(0, 10, size=n_samples),                   # merchant category
            np.random.exponential(scale=5, size=n_samples),             # distance from home
        ])

    def train(self) -> None:
        """Train the model on synthetic normal transaction data."""
        X_train = self.generate_training_data()
        X_scaled = self.scaler.fit_transform(X_train)
        self.model.fit(X_scaled)
        self.is_trained = True
        print("Model trained on 5000 normal transactions.")

    def score_transaction(self, transaction: dict) -> dict:
        """
        Score a single transaction in real time.

        Returns the transaction enriched with:
          - risk_score:    0.0 to 1.0 (higher = more suspicious)
          - is_fraud:      True if flagged as anomalous
          - decision:      "FRAUD" or "NORMAL"

        Isolation Forest returns:
          -1 = anomaly (fraud)
           1 = normal
        The decision_function returns a negative score for anomalies.
        We convert to a 0-1 risk score for readability.
        """
        if not self.is_trained:
            raise RuntimeError("Model must be trained before scoring.")

        features = np.array([[
            transaction["amount"],
            transaction["hour"],
            transaction["day_of_week"],
            transaction["merchant_category"],
            transaction["distance_from_home"],
        ]])

        features_scaled = self.scaler.transform(features)

        # decision_function: more negative = more anomalous
        raw_score = self.model.decision_function(features_scaled)[0]
        prediction = self.model.predict(features_scaled)[0]

        # Convert to 0-1 risk score (higher = riskier)
        # Raw scores typically range from -0.5 to 0.5
        risk_score = float(1 / (1 + np.exp(raw_score * 5)))

        return {
            **transaction,
            "risk_score": round(risk_score, 4),
            "is_fraud": bool(prediction == -1),
            "decision": "FRAUD" if prediction == -1 else "NORMAL",
        }