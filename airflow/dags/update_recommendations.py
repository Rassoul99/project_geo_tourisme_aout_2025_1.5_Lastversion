from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from app.utils.google_api import get_nearby_places, get_place_details
from app.utils.nlp_analysis import analyze_sentiments
import pandas as pd
import os

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'update_recommendations',
    default_args=default_args,
    schedule_interval='@weekly',
    catchup=False
)

def extract_places():
    cities = ["Paris", "London", "New York", "Tokyo", "Sydney"]
    all_data = []
    for city in cities:
        location = get_geocode_address(f"{city}, Country")
        if not location:
            continue
        for poi_type in ["restaurant", "hotel", "tourist_attraction"]:
            pois = get_nearby_places((location['lat'], location['lng']), 1000, poi_type)
            for poi in pois:
                details = get_place_details(poi['place_id'])
                all_data.append({
                    'city': city,
                    'name': poi.get('name'),
                    'type': poi.get('types', [None])[0],
                    'rating': details.get('rating'),
                    'reviews': details.get('reviews', []),
                    'latitude': details['geometry']['location']['lat'],
                    'longitude': details['geometry']['location']['lng']
                })
    df = pd.DataFrame(all_data)
    df.to_csv('/data/processed/places_with_reviews.csv', index=False)

def analyze_reviews():
    df = pd.read_csv('/data/processed/places_with_reviews.csv')
    df['sentiments'] = df['reviews'].apply(analyze_sentiments)
    df.to_csv('/data/recommendations/latest_recommendations.csv', index=False)

extract_task = PythonOperator(
    task_id='extract_places',
    python_callable=extract_places,
    dag=dag
)

analyze_task = PythonOperator(
    task_id='analyze_reviews',
    python_callable=analyze_reviews,
    dag=dag
)

extract_task >> analyze_task
