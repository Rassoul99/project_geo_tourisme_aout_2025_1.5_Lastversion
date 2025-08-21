import os
import requests
import time
from .config import cache_get, cache_set, get_cache_key

def get_geocode_address(address):
    """Géocodage avec cache"""
    cache_key = get_cache_key("geocode", address)
    cached = cache_get(cache_key)
    if cached:
        return cached
    try:
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={os.getenv('GOOGLE_PLACES_KEY')}"
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get('status') == 'OK' and data.get('results'):
            result = data['results'][0]['geometry']['location']
            cache_set(cache_key, result)
            return result
        return None
    except Exception as e:
        print(f"Erreur géocodage: {e}")
        return None

def get_nearby_places(location, radius, poi_type, use_cache=True):
    """Récupère les POI avec cache"""
    cache_key = get_cache_key("nearby", location, radius, poi_type)
    cached = cache_get(cache_key) if use_cache else None
    if cached:
        return cached

    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{location[0]},{location[1]}",
        "radius": max(int(radius), 50),  # FIX: sécurité min rayon
        "type": poi_type,
        "key": os.getenv('GOOGLE_PLACES_KEY')
    }
    all_results = []
    seen_place_ids = set()
    while True:
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            if data.get('status') not in ('OK', 'ZERO_RESULTS'):
                # Log soft
                print(f"Nearby status: {data.get('status')}, error_message: {data.get('error_message')}")
                break
            results = data.get('results', [])
            for r in results:
                pid = r.get('place_id')
                if pid and pid not in seen_place_ids:
                    all_results.append(r)
                    seen_place_ids.add(pid)
            if not data.get('next_page_token'):
                break
            params['pagetoken'] = data['next_page_token']
            time.sleep(2)  # backoff imposé par Google
        except Exception as e:
            print(f"Erreur POI: {e}")
            break

    if use_cache and all_results:
        cache_set(cache_key, all_results, ttl=3600)
    return all_results

def get_place_details(place_id, use_cache=True):
    """Récupération des détails avec cache"""
    cache_key = get_cache_key("place_details", place_id)
    cached = cache_get(cache_key) if use_cache else None
    if cached:
        return cached
    try:
        url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&key={os.getenv('GOOGLE_PLACES_KEY')}"
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get('status') == 'OK':
            result = data.get('result', {})
            if use_cache and result:
                cache_set(cache_key, result, ttl=3600)
            return result
        else:
            print(f"Details status: {data.get('status')}, error_message: {data.get('error_message')}")
            return {}
    except Exception as e:
        print(f"Erreur détails: {e}")
        return {}

# ---------- FIX: géolocalisation Google (optionnelle) ----------
def google_geolocate():
    """
    Utilise l'API Google Geolocation pour estimer la position de l'utilisateur (si clé disponible).
    Nécessite d'activer l'API "Geolocation" côté Google Cloud et d'utiliser la même clé que Places.
    Retourne un dict {'lat': float, 'lng': float} ou None.
    """
    api_key = os.getenv('GOOGLE_PLACES_KEY')
    if not api_key:
        return None
    try:
        url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={api_key}"
        # En POST, sans payload => Google utilise IP + signaux génériques
        resp = requests.post(url, json={}, timeout=5)
        data = resp.json()
        if data.get('location'):
            return {'lat': data['location']['lat'], 'lng': data['location']['lng']}
    except Exception as e:
        print(f"Erreur google_geolocate: {e}")
    return None
