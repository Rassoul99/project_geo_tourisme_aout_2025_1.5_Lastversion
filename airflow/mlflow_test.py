import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import pandas as pd
import os

# Set MLflow tracking URI to the service name in Docker network
mlflow.set_tracking_uri("http://mlflow:5000")
mlflow.set_experiment("Weather_Prediction")

# Load data
try:
    df = pd.read_csv('/opt/airflow/clean_data/fulldata.csv')
    X = df.drop('target', axis=1)
    y = df['target']

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train model
    with mlflow.start_run():
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)

        # Predict and evaluate
        predictions = model.predict(X_test)
        mse = mean_squared_error(y_test, predictions)

        # Log metrics
        mlflow.log_param("n_estimators", 100)
        mlflow.log_metric("mse", mse)

        # Log model
        mlflow.sklearn.log_model(model, "model")
        print(f"Model logged successfully with MSE: {mse}")

except Exception as e:
    print(f"Error in MLflow test: {e}")
    print("Please ensure the data file exists at /opt/airflow/clean_data/fulldata.csv")
