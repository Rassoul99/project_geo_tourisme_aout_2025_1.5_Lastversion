# Image légère avec Python
FROM python:3.9-slim

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code
WORKDIR /app
COPY . .

# Variables d'environnement
ENV PYTHONPATH=/app
ENV USE_CACHE=true

# Port exposé
EXPOSE 8501

# Commande de lancement
CMD ["streamlit", "run", "app/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
