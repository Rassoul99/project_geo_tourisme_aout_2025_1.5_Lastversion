# Import des bibliothèques nécessaires
from datetime import datetime, timedelta
from airflow.decorators import dag, task, task_group
from airflow.operators.python import PythonOperator
from airflow.models import Variable
import requests
import json
import os
import pandas as pd
from sklearn.model_selection import cross_val_score
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from joblib import dump

"""
# Weather Data Pipeline
Ce DAG récupère les données météo, les transforme et entraîne un modèle de prédiction.
"""
# Fonction pour récupérer les données météo
def fetch_weather_data(**kwargs):
    """
    Récupère les données météo depuis l'API OpenWeatherMap.
    Gère les erreurs de désérialisation de la variable 'cities'.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    try:
        cities = Variable.get("cities", deserialize_json=True)
        if not isinstance(cities, list):
            raise ValueError("La variable 'cities' n'est pas une liste valide.")
    except Exception as e:
        print(f"Erreur lors de la récupération de la variable 'cities': {e}")
        cities = ["paris","Clermont-Ferrand", "london", "washington"]  # Valeur par défaut

    data = []
    for city in cities:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}"
        response = requests.get(url)
        if response.status_code == 200:
            data.append(response.json())
        else:
            print(f"Échec de la récupération des données pour {city}")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    filename = f"/app/raw_files/{timestamp}.json"

    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, 'w') as file:
        json.dump(data, file)
# Fonction pour transformer les données en CSV
def transform_data_into_csv(n_files=None, filename='data.csv'):
    """Transforme les données JSON en fichiers CSV."""
    parent_folder = '/app/raw_files'
    os.makedirs(parent_folder, exist_ok=True)
    files = sorted(os.listdir(parent_folder), reverse=True)

    if n_files:
        files = files[:n_files]

    dfs = []
    for f in files:
        with open(os.path.join(parent_folder, f), 'r') as file:
            data_temp = json.load(file)
        for data_city in data_temp:
            dfs.append(
                {
                    'temperature': data_city['main']['temp'],
                    'city': data_city['name'],
                    'pression': data_city['main']['pressure'],
                    'date': f.split('.')[0]
                }
            )

    df = pd.DataFrame(dfs)
    output_path = f'/app/clean_data/{filename}'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
# Fonction pour calculer le score du modèle
def compute_model_score(model, X, y):
    """Calcule le score du modèle avec validation croisée."""
    cross_validation = cross_val_score(
        model,
        X,
        y,
        cv=3,
        scoring='neg_mean_squared_error'
    )
    model_score = cross_validation.mean()
    return model_score
# Fonction pour entraîner et sauvegarder le modèle
def train_and_save_model(model, X, y, path_to_model='./app/clean_data/best_model.pckl'):
    """Entraîne et sauvegarde le modèle."""
    model.fit(X, y)
    os.makedirs(os.path.dirname(path_to_model), exist_ok=True)
    dump(model, path_to_model)
# Fonction pour préparer les données
def prepare_data(path_to_data='/app/clean_data/fulldata.csv'):
    """Prépare les données pour l'entraînement du modèle."""
    df = pd.read_csv(path_to_data)
    df = df.sort_values(['city', 'date'], ascending=True)
    dfs = []
    for c in df['city'].unique():
        df_temp = df[df['city'] == c].copy()
        df_temp.loc[:, 'target'] = df_temp['temperature'].shift(1)

        for i in range(1, 10):
            df_temp.loc[:, f'temp_m-{i}'] = df_temp['temperature'].shift(-i)

        df_temp = df_temp.dropna()
        dfs.append(df_temp)

    df_final = pd.concat(dfs, axis=0, ignore_index=True)
    df_final = df_final.drop(['date'], axis=1)
    df_final = pd.get_dummies(df_final)

    features = df_final.drop(['target'], axis=1)
    target = df_final['target']

    return features, target
# Définition du DAG
@dag(
    dag_id='weather_data_pipeline',
    description='DAG pour récupérer, transformer et analyser les données météo',
    schedule_interval=timedelta(minutes=1),
    start_date=datetime(2023, 1, 1),
    catchup=False,
)
def weather_data_pipeline():

    @task(retries=5, retry_delay=timedelta(seconds=10))
    def fetch_weather_task():
        """Tâche pour récupérer les données météo, exécutée 5 fois."""
        fetch_weather_data()

    @task_group
    def transform_data_group():
        """Groupe de tâches pour transformer les données."""

        @task
        def transform_recent_data():
            """Transforme les 20 derniers fichiers en un fichier CSV."""
            transform_data_into_csv(n_files=20, filename='data.csv')

        @task
        def transform_full_data():
            """Transforme tous les fichiers en un fichier CSV."""
            transform_data_into_csv(filename='fulldata.csv')

        transform_recent_data() >> transform_full_data()

    @task_group
    def train_models_group():
        """Groupe de tâches pour entraîner les modèles."""

        @task
        def train_models():
            """Entraîne les modèles et sauvegarde le meilleur."""
            X, y = prepare_data('/app/clean_data/fulldata.csv')
            score_lr = compute_model_score(LinearRegression(), X, y)
            score_dt = compute_model_score(DecisionTreeRegressor(), X, y)

            if score_lr < score_dt:
                train_and_save_model(
                    LinearRegression(),
                    X,
                    y,
                    '/app/clean_data/best_model.pickle'
                )
            else:
                train_and_save_model(
                    DecisionTreeRegressor(),
                    X,
                    y,
                    '/app/clean_data/best_model.pickle'
                )

        train_models()

    fetch_weather_task = fetch_weather_task()
    transform_data = transform_data_group()
    train_models = train_models_group()

    fetch_weather_task >> transform_data >> train_models

weather_dag = weather_data_pipeline()


# This code defines a DAG for Airflow that fetches weather data, transforms it, and trains a model.
# The DAG is structured using decorators for better readability and maintainability.

# Additional configuration and error handling could be added here
# For example, adding retry logic, email notifications on failure, or data validation steps
# to ensure the integrity of the data being processed.