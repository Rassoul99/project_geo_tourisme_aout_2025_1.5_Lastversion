from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
import requests
import json
import os
import pandas as pd
from joblib import dump
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.model_selection import cross_val_score

def fetch_travel_data(**kwargs):
    """Fetch travel data from Google Places API"""
    api_key = os.getenv("GOOGLE_PLACES_KEY")
    cities = Variable.get("cities", deserialize_json=True, default_var=["Paris", "Lyon", "Marseille"])
    data = []

    for city in cities:
        url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={city}&key={api_key}"
        response = requests.get(url)
        if response.status_code == 200:
            data.append(response.json())
        else:
            print(f"Failed to fetch data for {city}")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M")
    filename = f"/opt/airflow/raw_files/google_places_{timestamp}.json"

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as file:
        json.dump(data, file)

def fetch_datatourisme_data(**kwargs):
    """Fetch travel data from DATAtourisme API"""
    api_key = "d7b3b49e-58d1-4ca4-9e7c-3c0c93f79306"
    cities = Variable.get("cities", deserialize_json=True, default_var=["Paris", "Lyon", "Marseille"])
    data = []

    for city in cities:
        url = f"https://api.datatourisme.fr/v1/places?location={city}&radius=5000"
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data.append(response.json())
        else:
            print(f"Failed to fetch data for {city}")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M")
    filename = f"/opt/airflow/raw_files/datatourisme_{timestamp}.json"

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as file:
        json.dump(data, file)

def process_travel_data():
    """Process and combine travel data from both sources"""
    google_files = [f for f in os.listdir("/opt/airflow/raw_files") if f.startswith("google_places_")]
    datatourisme_files = [f for f in os.listdir("/opt/airflow/raw_files") if f.startswith("datatourisme_")]

    all_data = []

    # Process Google Places data
    for f in google_files:
        with open(f"/opt/airflow/raw_files/{f}", 'r') as file:
            data = json.load(file)
            for city_data in data:
                for result in city_data.get('results', []):
                    all_data.append({
                        'source': 'google',
                        'name': result.get('name'),
                        'address': result.get('formatted_address'),
                        'latitude': result.get('geometry', {}).get('location', {}).get('lat'),
                        'longitude': result.get('geometry', {}).get('location', {}).get('lng'),
                        'rating': result.get('rating'),
                        'types': result.get('types'),
                        'date': f.split('_')[0]
                    })

    # Process DATAtourisme data
    for f in datatourisme_files:
        with open(f"/opt/airflow/raw_files/{f}", 'r') as file:
            data = json.load(file)
            for city_data in data:
                for result in city_data.get('results', []):
                    all_data.append({
                        'source': 'datatourisme',
                        'name': result.get('name'),
                        'address': result.get('address'),
                        'latitude': result.get('latitude'),
                        'longitude': result.get('longitude'),
                        'rating': result.get('rating'),
                        'types': result.get('google_types', []),
                        'date': f.split('_')[0]
                    })

    # Save combined data
    df = pd.DataFrame(all_data)
    output_path = "/opt/airflow/clean_data/combined_travel_data.csv"
    df.to_csv(output_path, index=False)

    # Save metrics for Dashboard
    metrics = {
        'google_places_count': len([d for d in all_data if d['source'] == 'google']),
        'datatourisme_count': len([d for d in all_data if d['source'] == 'datatourisme']),
        'total_locations': len(all_data),
        'avg_rating': df['rating'].mean()
    }

    metrics_path = "/opt/airflow/clean_data/travel_metrics.json"
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f)

# Define the DAG
dag = DAG(
    'travel_data_pipeline',
    description='Pipeline for fetching and processing travel data',
    schedule_interval=timedelta(hours=1),
    start_date=datetime(2023, 1, 1),
    catchup=False,
)

# Define tasks
fetch_google_task = PythonOperator(
    task_id='fetch_google_places_data',
    python_callable=fetch_travel_data,
    dag=dag,
)

fetch_datatourisme_task = PythonOperator(
    task_id='fetch_datatourisme_data',
    python_callable=fetch_datatourisme_data,
    dag=dag,
)

process_data_task = PythonOperator(
    task_id='process_travel_data',
    python_callable=process_travel_data,
    dag=dag,
)

# Set task dependencies
[fetch_google_task, fetch_datatourisme_task] >> process_data_task
