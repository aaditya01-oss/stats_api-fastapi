"""
weather_pipeline.py — Our first Airflow DAG.

This pipeline runs every hour and:
  1. Extracts weather data from a free public API
  2. Transforms it — cleans and validates the data
  3. Loads it into PostgreSQL

A DAG is just a Python file. Airflow reads it,
understands the task order, and runs it on schedule.
"""

from datetime import datetime, timedelta
import requests
import psycopg2
import json

from airflow import DAG
from airflow.operators.python import PythonOperator


# ── DAG configuration ──────────────────────────────────────────────
# default_args apply to every task in the DAG
default_args = {
    "owner": "aaditya",
    "retries": 1,                         # retry once if a task fails
    "retry_delay": timedelta(minutes=5),  # wait 5 mins before retry
    "email_on_failure": False,
}

# The DAG object — this is what Airflow reads
dag = DAG(
    "weather_pipeline",           # unique name
    default_args=default_args,
    description="Hourly weather ETL pipeline",
    schedule_interval="@hourly",  # run every hour
    start_date=datetime(2024, 1, 1),
    catchup=False,                # don't run for past dates
    tags=["etl", "weather"],
)


# ── Database connection helper ─────────────────────────────────────
def get_db_connection():
    """
    Returns a PostgreSQL connection.
    psycopg2 is the Python driver for PostgreSQL —
    it's what lets Python talk to the database.
    """
    return psycopg2.connect(
        host="postgres",       # the service name in docker-compose
        database="airflow",
        user="airflow",
        password="airflow",
        port=5432,
    )


# ── Task 1: Extract ────────────────────────────────────────────────
def extract_weather(**context):
    """
    Pulls current weather data for Kathmandu from a free API.
    Open-Meteo is completely free, no API key needed.

    **context is Airflow's context dictionary — it contains info
    about the current run (execution date, run ID, etc.).
    We use it to pass data between tasks via XCom.
    """
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=27.7172"
        "&longitude=85.3240"
        "&current_weather=true"
        "&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m"
    )

    print(f"Fetching weather data from: {url}")
    response = requests.get(url, timeout=30)

    # Raise an exception if the request failed (4xx or 5xx status)
    response.raise_for_status()

    raw_data = response.json()
    print(f"Raw data received: {json.dumps(raw_data, indent=2)[:200]}...")

    # XCom (Cross-Communication) lets tasks pass data to each other.
    # task_instance.xcom_push stores a value under a key.
    # The next task pulls it with xcom_pull.
    context["task_instance"].xcom_push(key="raw_weather", value=raw_data)
    print("Extract complete.")


# ── Task 2: Transform ──────────────────────────────────────────────
def transform_weather(**context):
    """
    Cleans and validates the raw data.

    Transform rules:
    - Extract only the fields we care about
    - Validate temperature is in a reasonable range
    - Add a timestamp for when we collected this data
    - Return a clean, flat dictionary ready for the database
    """
    # Pull the raw data from the Extract task
    raw_data = context["task_instance"].xcom_pull(
        key="raw_weather",
        task_ids="extract_weather"
    )

    if not raw_data:
        raise ValueError("No data received from extract task.")

    current = raw_data.get("current_weather", {})

    # Validate temperature
    temperature = current.get("temperature")
    if temperature is None:
        raise ValueError("Temperature missing from API response.")
    if not (-60 <= temperature <= 60):
        raise ValueError(f"Temperature {temperature} is out of valid range.")

    # Build the clean record
    clean_record = {
        "city": "Kathmandu",
        "latitude": 27.7172,
        "longitude": 85.3240,
        "temperature_c": temperature,
        "wind_speed_kmh": current.get("windspeed"),
        "weather_code": current.get("weathercode"),
        "is_day": bool(current.get("is_day", 1)),
        "collected_at": datetime.utcnow().isoformat(),
        "api_time": current.get("time"),
    }

    print(f"Transformed record: {clean_record}")

    # Push clean record for the Load task
    context["task_instance"].xcom_push(key="clean_weather", value=clean_record)
    print("Transform complete.")


# ── Task 3: Load ───────────────────────────────────────────────────
def load_weather(**context):
    """
    Writes the clean record to PostgreSQL.

    IF NOT EXISTS means we create the table on first run
    and skip if it already exists on subsequent runs.
    This makes the task idempotent — safe to run multiple times.
    """
    clean_record = context["task_instance"].xcom_pull(
        key="clean_weather",
        task_ids="transform_weather"
    )

    if not clean_record:
        raise ValueError("No data received from transform task.")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weather_data (
            id              SERIAL PRIMARY KEY,
            city            VARCHAR(100),
            latitude        FLOAT,
            longitude       FLOAT,
            temperature_c   FLOAT,
            wind_speed_kmh  FLOAT,
            weather_code    INT,
            is_day          BOOLEAN,
            collected_at    TIMESTAMP,
            api_time        VARCHAR(50)
        );
    """)

    # Insert the record
    cursor.execute("""
        INSERT INTO weather_data (
            city, latitude, longitude, temperature_c,
            wind_speed_kmh, weather_code, is_day,
            collected_at, api_time
        ) VALUES (
            %(city)s, %(latitude)s, %(longitude)s, %(temperature_c)s,
            %(wind_speed_kmh)s, %(weather_code)s, %(is_day)s,
            %(collected_at)s, %(api_time)s
        );
    """, clean_record)

    # commit() makes the insert permanent
    # Without this, the data exists only in a transaction and disappears
    conn.commit()

    # Always close connections — leaving them open leaks resources
    cursor.close()
    conn.close()

    print(f"Successfully loaded weather record for {clean_record['city']}")
    print("Load complete.")


# ── Wire tasks together ────────────────────────────────────────────
# Create task objects from the functions above
extract_task = PythonOperator(
    task_id="extract_weather",
    python_callable=extract_weather,
    dag=dag,
    provide_context=True,
)

transform_task = PythonOperator(
    task_id="transform_weather",
    python_callable=transform_weather,
    dag=dag,
    provide_context=True,
)

load_task = PythonOperator(
    task_id="load_weather",
    python_callable=load_weather,
    dag=dag,
    provide_context=True,
)

# >> is Airflow's syntax for "runs before"
# extract → transform → load
extract_task >> transform_task >> load_task