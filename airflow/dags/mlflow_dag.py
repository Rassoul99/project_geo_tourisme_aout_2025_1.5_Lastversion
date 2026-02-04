from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import pandas as pd
import os

def train_model_with_mlflow():
    try:
        # Set MLflow tracking URI to the service name in Docker network
        mlflow.set_tracking_uri("http://mlflow:5000")
        mlflow.set_experiment("Weather_Prediction_Airflow")

        # Load data
        data_path = '/opt/airflow/clean_data/fulldata.csv'
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"Data file not found at {data_path}")

        df = pd.read_csv(data_path)

        # Prepare data
        X = df.drop(['target', 'city'], axis=1)
        y = df['target']

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Start MLflow run
        with mlflow.start_run():
            # Train model
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X_train, y_train)

            # Predict and evaluate
            predictions = model.predict(X_test)
            mse = mean_squared_error(y_test, predictions)

            # Log parameters and metrics
            mlflow.log_param("n_estimators", 100)
            mlflow.log_metric("mse", mse)

            # Log model
            mlflow.sklearn.log_model(model, "model")

            # Save model for dashboard
            model_path = '/opt/airflow/models/weather_model.pkl'
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            mlflow.sklearn.save_model(model, model_path)

            print(f"Model trained and logged successfully with MSE: {mse}")

    except Exception as e:
        print(f"Error in MLflow DAG: {e}")
        raise

dag = DAG(
    'mlflow_weather_pipeline',
    description='DAG for training weather prediction model with MLflow',
    schedule_interval=timedelta(hours=1),
    start_date=datetime(2023, 1, 1),
    catchup=False,
)

train_model_task = PythonOperator(
    task_id='train_model_with_mlflow',
    python_callable=train_model_with_mlflow,
    dag=dag,
)
