import os
import json
import hashlib
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

STATIC_CITIES = {
    "Paris": {
        "lat": 48.8566,
        "lng": 2.3522,
        "pois": {
            "restaurant": [
                {"name": "Le Bistrot Parisien", "latitude": 48.8561, "longitude": 2.3525, "rating": 4.5},
                {"name": "Chez Janou", "latitude": 48.8562, "longitude": 2.3526, "rating": 4.7}
            ],
            "hotel": [
                {"name": "Hôtel Luxe Paris", "latitude": 48.8560, "longitude": 2.3524, "rating": 4.8}
            ],
            "tourist_attraction": [
                {"name": "Tour Eiffel", "latitude": 48.8584, "longitude": 2.2945, "rating": 4.9}
            ]
        }
    },
    "Londres": {
        "lat": 51.5074,
        "lng": -0.1278,
        "pois": {
            "restaurant": [
                {"name": "The Wolseley", "latitude": 51.5085, "longitude": -0.1280, "rating": 4.6}
            ],
            "hotel": [
                {"name": "The Savoy", "latitude": 51.5086, "longitude": -0.1281, "rating": 4.8}
            ],
            "tourist_attraction": [
                {"name": "Big Ben", "latitude": 51.5007, "longitude": -0.1246, "rating": 4.8}
            ]
        }
    }
}

def load_config():
    """Charge la configuration et active le cache"""
    os.environ["USE_CACHE"] = "true"  # Activer le cache par défaut

def get_cache_key(*args):
    """Génère une clé de cache unique"""
    key = "_".join(str(arg) for arg in args)
    return hashlib.md5(key.encode()).hexdigest()

def cache_get(key):
    """Récupère des données depuis le cache"""
    cache_file = CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        with open(cache_file, 'r') as f:
            return json.load(f)
    return None

def cache_set(key, data, ttl=86400):
    """Sauvegarde des données en cache (24h par défaut)"""
    cache_file = CACHE_DIR / f"{key}.json"
    with open(cache_file, 'w') as f:
        json.dump(data, f)
