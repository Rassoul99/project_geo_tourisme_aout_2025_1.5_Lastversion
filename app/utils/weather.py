import os
import requests

def get_weather_forecast(lat, lng):
    """
    Récupère la météo actuelle via OpenWeatherMap (gratuit) avec détection explicite de précipitations.
    Si OpenWeatherMap n'est pas disponible, utilise l'API de météo de GCP comme alternative.
    """
    # Essayer d'abord avec OpenWeatherMap
    openweather_data = get_openweathermap_forecast(lat, lng)
    if openweather_data:
        return openweather_data

    # Si OpenWeatherMap échoue ou si les données ne sont pas disponibles, utilisez GCP Weather API
    return get_gcp_weather_forecast(lat, lng)

def get_openweathermap_forecast(lat, lng):
    """Récupère la météo actuelle via OpenWeatherMap."""
    api_key = os.getenv("OPENWEATHERMAP_KEY")
    if not api_key:
        return None
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lng}&appid={api_key}&units=metric&lang=fr"
        response = requests.get(url, timeout=6)
        data = response.json()
        if data.get('cod') == 200:
            weather_list = data.get('weather', [])
            description = weather_list[0]['description'].capitalize() if weather_list else 'N/A'
            # Si champs rain/snow existent, on l’indique dans la description
            if data.get('rain', {}).get('1h'):
                description = f"{description} (Pluie {data['rain']['1h']} mm sur 1h)"
            elif data.get('snow', {}).get('1h'):
                description = f"{description} (Neige {data['snow']['1h']} mm sur 1h)"
            return {
                'temp': round(data['main']['temp']),
                'description': description,
                'icon': weather_list[0].get('icon') if weather_list else None
            }
        else:
            print(f"Erreur météo: {data.get('message', 'Unknown error')}")
            return None
    except Exception as e:
        print(f"Erreur réseau pour OpenWeatherMap: {e}")
        return None

def get_gcp_weather_forecast(lat, lng):
    """
    Récupère la météo actuelle via une API fictive de GCP (à remplacer par l'API réelle si disponible).
    Notez que cette fonction est un exemple et que les détails spécifiques dépendent de l'API réelle de GCP.
    """
    # Remplacez par l'endpoint réel de l'API de météo de GCP
    api_key = os.getenv("GCP_WEATHER_API_KEY")
    if not api_key:
        return None
    try:
        # Exemple d'URL, à remplacer par l'URL réelle de l'API de GCP
        url = f"https://weather.googleapis.com/v1/locations:{lat},{lng}/forecast?key={api_key}"
        response = requests.get(url, timeout=6)
        data = response.json()

        # Traitez les données de la réponse selon la structure réelle de l'API GCP
        # Ceci est un exemple hypothétique. Adaptez-le selon la documentation de l'API.
        if 'forecasts' in data and data['forecasts']:
            forecast = data['forecasts'][0]
            return {
                'temp': round(forecast['temperature']),
                'description': forecast.get('conditions', 'N/A'),
                'icon': forecast.get('icon')  # Si disponible
            }
        else:
            print(f"Erreur avec l'API GCP: {data.get('error', {}).get('message', 'Unknown error')}")
            return None
    except Exception as e:
        print(f"Erreur réseau pour l'API GCP: {e}")
        return None
