import os
import requests

def get_viator_activities(lat, lng, poi_name):
    """Récupère les activités Viator proches d'un POI (rayon 5km)."""
    api_key = os.getenv("VIATOR_API_KEY", "8cd8a095-d7c6-47ea-a0e7-9afacc40a0c5")
    if not api_key:
        return []

    try:
        url = "https://api.viator.com/partner/products/search"
        params = {
            "apiKey": api_key,
            "lat": lat,
            "lng": lng,
            "radius": 5,  # 5 km autour du POI
            "q": poi_name or "",
            "limit": 3    # Limiter à 3 résultats
        }

        response = requests.get(url, params=params, timeout=6)
        data = response.json()

        items = data.get('data') or []
        results = []
        for item in items[:3]:
            title = item.get('title') or "Activité"
            url_item = item.get('url') or item.get('productUrl') or "#"
            price = None
            if item.get('price') and isinstance(item['price'], dict):
                price = item['price'].get('formattedDisplayPrice') or item['price'].get('fromPriceFormatted')
            results.append({
                'title': title,
                'url': url_item,
                'price': price or "—"
            })
        return results
    except Exception as e:
        print(f"Erreur Viator: {e}")
        return []
