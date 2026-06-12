"""
train.py — ML training with MLflow experiment tracking.

We train a model to predict whether a city's temperature
is above or below average — using the weather data we
collected with our Airflow pipeline in Month 4.

For simplicity we generate synthetic weather data here,
but in a real project you'd pull it from PostgreSQL.

What MLflow tracks automatically for every run:
  - Parameters: the hyperparameters you chose
  - Metrics: how well the model performed
  - Artifacts: the actual saved model file
  - Code version: which git commit produced this run
  - Timestamp: exactly when it ran
"""

import mlflow
import mlflow.sklearn
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.preprocessing import StandardScaler

import os

# Reads from environment variable — works both locally and in Docker

# ── Tell MLflow where the tracking server is ──────────────────────
# This is the MLflow container we just added to docker-compose.
# When running locally (outside Docker), point to localhost.
mlflow.set_tracking_uri(
    os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
)

# ── Create or reuse an experiment ─────────────────────────────────
# An experiment groups related runs together.
# Think of it like a folder for all your "weather prediction" attempts.
mlflow.set_experiment("weather_temperature_prediction")


def generate_weather_data(n_samples: int = 1000) -> pd.DataFrame:
    """
    Generates synthetic weather data.
    In a real project: SELECT * FROM weather_data in PostgreSQL.

    Features:
      - wind_speed_kmh: wind speed
      - humidity: relative humidity percentage
      - pressure_hpa: atmospheric pressure
      - hour_of_day: 0-23

    Target:
      - is_hot: 1 if temperature > 25°C, 0 otherwise
    """
    np.random.seed(42)
    df = pd.DataFrame({
        "wind_speed_kmh": np.random.exponential(scale=10, size=n_samples),
        "humidity":       np.random.normal(loc=65, scale=15, size=n_samples).clip(0, 100),
        "pressure_hpa":   np.random.normal(loc=1013, scale=8, size=n_samples),
        "hour_of_day":    np.random.randint(0, 24, size=n_samples),
    })
    # Temperature is loosely correlated with humidity (inverse) and hour
    temperature = (
        30
        - 0.1 * df["humidity"]
        + 2 * np.sin(np.pi * df["hour_of_day"] / 12)
        + np.random.normal(0, 3, n_samples)
    )
    df["is_hot"] = (temperature > 25).astype(int)
    return df


def train_and_log(
    model_type: str = "random_forest",
    n_estimators: int = 100,
    max_depth: int = 5,
    C: float = 1.0,
) -> None:
    """
    Trains one model and logs everything to MLflow.

    Every call to this function creates one "run" in MLflow —
    a complete record of one experiment attempt.

    Args:
        model_type:    "random_forest" or "logistic_regression"
        n_estimators:  number of trees (random forest only)
        max_depth:     tree depth (random forest only)
        C:             regularisation strength (logistic regression only)
    """
    df = generate_weather_data()
    X = df.drop("is_hot", axis=1)
    y = df["is_hot"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # ── Start an MLflow run ────────────────────────────────────────
    # Everything inside this block gets logged to MLflow.
    # The run_name makes it easy to find in the UI.
    with mlflow.start_run(run_name=f"{model_type}_d{max_depth}_n{n_estimators}"):

        # ── Log parameters ─────────────────────────────────────────
        # Parameters = the choices YOU made before training.
        # These are the knobs you turned.
        mlflow.log_param("model_type", model_type)
        mlflow.log_param("n_samples", len(df))
        mlflow.log_param("test_size", 0.2)

        # ── Build and train the model ──────────────────────────────
        if model_type == "random_forest":
            mlflow.log_param("n_estimators", n_estimators)
            mlflow.log_param("max_depth", max_depth)
            model = RandomForestClassifier(
                n_estimators=n_estimators,
                max_depth=max_depth,
                random_state=42,
            )
        else:
            scaler = StandardScaler()
            X_train = scaler.fit_transform(X_train)
            X_test  = scaler.transform(X_test)
            mlflow.log_param("C", C)
            model = LogisticRegression(C=C, random_state=42, max_iter=1000)

        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        # ── Log metrics ────────────────────────────────────────────
        # Metrics = how well the model performed.
        # These are the results you measured AFTER training.
        accuracy  = accuracy_score(y_test, y_pred)
        f1        = f1_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred)
        recall    = recall_score(y_test, y_pred)

        mlflow.log_metric("accuracy", accuracy)
        mlflow.log_metric("f1_score", f1)
        mlflow.log_metric("precision", precision)
        mlflow.log_metric("recall", recall)

        # ── Log the model itself ───────────────────────────────────
        # This saves the actual trained model file as an artifact.
        # You can load it later with mlflow.sklearn.load_model(...)
        mlflow.sklearn.log_model(model, "model")

        print(f"\n{'='*50}")
        print(f"Model:     {model_type}")
        print(f"Accuracy:  {accuracy:.4f}")
        print(f"F1 Score:  {f1:.4f}")
        print(f"Precision: {precision:.4f}")
        print(f"Recall:    {recall:.4f}")
        print(f"{'='*50}\n")


if __name__ == "__main__":
    print("Starting MLflow experiment tracking...\n")
    print("Running 6 experiments with different models and hyperparameters...\n")

    # Run 1: Random Forest baseline
    train_and_log("random_forest", n_estimators=50, max_depth=3)

    # Run 2: Deeper Random Forest
    train_and_log("random_forest", n_estimators=100, max_depth=5)

    # Run 3: Even deeper Random Forest
    train_and_log("random_forest", n_estimators=200, max_depth=10)

    # Run 4: Logistic Regression baseline
    train_and_log("logistic_regression", C=0.1)

    # Run 5: Stronger regularisation
    train_and_log("logistic_regression", C=1.0)

    # Run 6: Weak regularisation
    train_and_log("logistic_regression", C=10.0)

    print("\nAll runs complete!")
    print("Open http://localhost:5000 to see all experiments in MLflow UI")