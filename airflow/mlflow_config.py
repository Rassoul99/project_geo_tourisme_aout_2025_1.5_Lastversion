import os

# Configuration for MLflow
MLFLOW_TRACKING_URI = "http://mlflow:5000"
MLFLOW_EXPERIMENT_NAME = "Weather_Prediction"

# MinIO configuration for artifact storage
MLFLOW_S3_ENDPOINT_URL = "http://minio:9000"
AWS_ACCESS_KEY_ID = "minioadmin"
AWS_SECRET_ACCESS_KEY = "minioadmin"
