from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
import requests
import json
import os

"""
# Test Weather Data Import

Ce DAG teste l'importation des données météo depuis l'API OpenWeatherMap.
"""

def fetch_weather_data(**kwargs):
    """
    Récupère les données météo depuis l'API OpenWeatherMap.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    cities = Variable.get("cities", deserialize_json=True)
    data = []

    for city in cities:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}"
        response = requests.get(url)
        if response.status_code == 200:
            data.append(response.json())
        else:
            print(f"Failed to fetch data for {city}")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M")
    filename = f"/opt/airflow/raw_files/{timestamp}.json"

    # Assurez-vous que le dossier existe
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, 'w') as file:
        json.dump(data, file)

# Définition du DAG
dag = DAG(
    'test_weather_import',
    description='Test DAG pour importer des données météo',
    schedule_interval=timedelta(minutes=1),
    start_date=datetime(2023, 1, 1),
    catchup=False,
)

# Tâche pour récupérer les données météo
fetch_weather_task = PythonOperator(
    task_id='fetch_weather_data',
    python_callable=fetch_weather_data,
    dag=dag,
)

fetch_weather_task
