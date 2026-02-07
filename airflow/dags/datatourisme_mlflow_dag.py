# Fichier: datatourisme_mlflow_dag.py
# À placer dans votre dossier dags/ d'Airflow

# Voici un DAG Airflow complet pour tester l'intégration de l'API DATAtourisme avec MLflow. Ce DAG inclut toutes les étapes nécessaires pour récupérer les données, les traiter et entraîner un modèle ML :
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
import requests
import json
import os
import pandas as pd
import mlflow
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from joblib import dump

# Configuration de l'API DATAtourisme
DATATOURISME_API_KEY = "d7b3b49e-58d1-4ca4-9e7c-3c0c93f79306"
BASE_URL = "https://api.datatourisme.fr/v1"

def fetch_datatourisme_data(**kwargs):
    """
    Récupère les données de DATAtourisme pour plusieurs villes
    et sauvegarde les résultats dans un fichier JSON
    """
    cities = Variable.get("cities", deserialize_json=True, default_var=["Paris", "Lyon", "Marseille"])
    data = []

    for city in cities:
        # Coordonnées approximatives des villes (à adapter selon vos besoins)
        city_coords = {
            "Paris": "48.8566,2.3522",
            "Lyon": "45.7640,4.8357",
            "Marseille": "43.2965,5.3698"
        }

        if city in city_coords:
            geo_params = f"{city_coords[city]},5km"  # Recherche dans un rayon de 5km
            endpoint = f"{BASE_URL}/catalog"

            params = {
                "geo_distance": geo_params,
                "page_size": 50,
                "fields": "uuid,label,type,isLocatedAt.geo,isLocatedAt.address,hasReview.hasReviewValue"
            }

            headers = {
                "X-API-Key": DATATOURISME_API_KEY
            }

            try:
                response = requests.get(endpoint, headers=headers, params=params)
                response.raise_for_status()
                city_data = response.json()
                data.append({
                    "city": city,
                    "results": city_data.get('objects', []),
                    "timestamp": datetime.now().isoformat()
                })
                print(f"Succès pour {city}: {len(city_data.get('objects', []))} résultats")
            except Exception as e:
                print(f"Erreur pour {city}: {e}")
                data.append({
                    "city": city,
                    "results": [],
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                })

    # Sauvegarde des résultats
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"/opt/airflow/raw_files/datatourisme_{timestamp}.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Données sauvegardées dans {output_path}")
    return output_path

def process_datatourisme_data(**kwargs):
    """
    Traite les données de DATAtourisme et crée un dataset pour le ML
    """
    ti = kwargs['ti']
    raw_file = ti.xcom_pull(task_ids='fetch_datatourisme_data')

    with open(raw_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    processed_data = []

    for city_data in data:
        for poi in city_data.get('results', []):
            # Extraire les informations pertinentes pour le ML
            processed_poi = {
                'city': city_data['city'],
                'label': poi.get('label', ''),
                'type': poi.get('type', ''),
                'latitude': poi.get('isLocatedAt', {}).get('geo', {}).get('latitude'),
                'longitude': poi.get('isLocatedAt', {}).get('geo', {}).get('longitude'),
                'rating': poi.get('hasReview', [{}])[0].get('hasReviewValue') if poi.get('hasReview') else None,
                'address': poi.get('isLocatedAt', {}).get('address', {}).get('formattedAddress', '')
            }
            processed_data.append(processed_poi)

    # Créer un DataFrame
    df = pd.DataFrame(processed_data)

    # Nettoyage des données
    df = df.dropna(subset=['latitude', 'longitude'])
    df['rating'] = df['rating'].fillna(0)

    # Sauvegarde du dataset traité
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"/opt/airflow/clean_data/datatourisme_processed_{timestamp}.csv"
    df.to_csv(output_path, index=False)

    print(f"Dataset traité sauvegardé dans {output_path}")
    return output_path

def train_ml_model_with_mlflow(**kwargs):
    """
    Entraîne un modèle ML et enregistre les résultats dans MLflow
    """
    ti = kwargs['ti']
    processed_file = ti.xcom_pull(task_ids='process_datatourisme_data')

    # Charger les données traitées
    df = pd.read_csv(processed_file)

    # Préparation des données pour le ML
    # Dans cet exemple, nous essayons de prédire la note (rating) en fonction des autres caractéristiques
    X = df.drop(['label', 'rating', 'address'], axis=1)
    y = df['rating']

    # Transformation des variables catégorielles
    X = pd.get_dummies(X, columns=['city', 'type'])

    # Séparation train/test
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Configuration MLflow
    mlflow.set_tracking_uri("http://mlflow:5000")  # Utilise le nom du service dans le réseau Docker
    mlflow.set_experiment("DATAtourisme_Recommendations")

    # Entraînement du modèle
    with mlflow.start_run():
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)

        # Prédictions et évaluation
        predictions = model.predict(X_test)
        mse = mean_squared_error(y_test, predictions)
        rmse = mse ** 0.5

        # Log des paramètres et métriques
        mlflow.log_param("n_estimators", 100)
        mlflow.log_metric("mse", mse)
        mlflow.log_metric("rmse", rmse)

        # Log du modèle
        mlflow.sklearn.log_model(model, "model")

        # Sauvegarde du modèle localement
        model_path = "/opt/airflow/models/datatourisme_model.pkl"
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        dump(model, model_path)

        print(f"Modèle entraîné avec succès. MSE: {mse:.4f}, RMSE: {rmse:.4f}")
        return {
            'mse': mse,
            'rmse': rmse,
            'model_path': model_path,
            'mlflow_run_id': mlflow.active_run().info.run_id
        }

# Définition du DAG
default_args = {
    'owner': 'Khadim Fall',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': False
}

dag = DAG(
    'datatourisme_mlflow_pipeline',
    default_args=default_args,
    description='Pipeline pour récupérer les données DATAtourisme, les traiter et entraîner un modèle ML avec MLflow',
    schedule_interval=timedelta(hours=1),
    catchup=False,
)

# Définition des tâches
fetch_data_task = PythonOperator(
    task_id='fetch_datatourisme_data',
    python_callable=fetch_datatourisme_data,
    dag=dag,
)

process_data_task = PythonOperator(
    task_id='process_datatourisme_data',
    python_callable=process_datatourisme_data,
    dag=dag,
)

train_model_task = PythonOperator(
    task_id='train_ml_model_with_mlflow',
    python_callable=train_ml_model_with_mlflow,
    dag=dag,
)

# Définition des dépendances entre les tâches
fetch_data_task >> process_data_task >> train_model_task

# Vous pouvez ajouter cette ligne pour tester le DAG manuellement dans le terminal
# if __name__ == "__main__":
#     dag.test()
