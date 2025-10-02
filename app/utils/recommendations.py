import pandas as pd
from datetime import datetime, timedelta
from geopy.distance import geodesic

def generate_recommendations(df, min_rating=4.0, stay_duration=1, time_preferences=None, weather=None, user_age=None, events=None):
    """
    Génère des recommandations optimisées avec:
    - 1 hôtel par jour
    - 2 restaurants par jour max
    - 1 activité par créneau horaire
    - Prise en compte de la météo
    - Filtrage par note minimale
    - Adaptation pour les moins de 26 ans (musées gratuits)
    """
    if df is None or df.empty:
        return {}
    # FIX: robustesse sur colonnes
    for col in ['rating', 'place_id', 'type', 'name', 'latitude', 'longitude']:
        if col not in df.columns:
            df[col] = None
    # Filtrage par note
    df = df[pd.to_numeric(df['rating'], errors='coerce').fillna(0) >= float(min_rating)]
    df = df.drop_duplicates(subset=['place_id'])
    # FIX: s'assurer que 'hotel' est bien reconnu même si Google renvoie 'lodging' en amont
    hotels = df[df['type'] == 'hotel'].copy()
    restaurants = df[df['type'] == 'restaurant'].copy()
    attractions = df[df['type'] == 'tourist_attraction'].copy()
    # Tri simple par note puis distance (si dispo)
    def _sort_block(block):
        if block.empty:
            return block
        sort_cols = ['rating']
        ascending = [False]
        if 'distance' in block.columns:
            sort_cols.append('distance')
            ascending.append(True)
        return block.sort_values(by=sort_cols, ascending=ascending)
    hotels = _sort_block(hotels)
    restaurants = _sort_block(restaurants)
    attractions = _sort_block(attractions)
    recommendations = {}
    if time_preferences is None:
        time_preferences = []
    # Indices pour éviter de reprendre le même POI
    h_idx = 0
    r_idx = 0
    a_idx = 0
    for day in range(1, stay_duration + 1):
        day_key = f"Day {day}"
        recommendations[day_key] = []
        # Sélection 1 hôtel par jour si dispo
        if not hotels.empty and h_idx < len(hotels):
            selected_hotel = hotels.iloc[h_idx].to_dict()
            recommendations[day_key].append(selected_hotel)
            h_idx += 1
        # Pour chaque créneau horaire, 1 restaurant + 1 attraction
        for time_slot in time_preferences:
            # Limite à 2 restaurants par jour
            if not restaurants.empty and r_idx < len(restaurants) and r_idx < 2:
                selected_restaurant = restaurants.iloc[r_idx].to_dict()
                selected_restaurant['time_slot'] = time_slot
                recommendations[day_key].append(selected_restaurant)
                r_idx += 1
            if not attractions.empty and a_idx < len(attractions):
                selected_attraction = attractions.iloc[a_idx].to_dict()
                # FIX: météo — si pluie/orage/bruine/neige, prioriser indoor (simple heuristique par mots-clés)
                if weather:
                    desc = (weather.get('description') or '').lower()
                    if any(k in desc for k in ['pluie', 'orage', 'bruine', 'neige']):
                        indoor_mask = attractions['name'].str.contains('musée|galerie|cinéma|aquarium|centre commercial|escape game', case=False, na=False)
                        indoor_attractions = attractions[indoor_mask]
                        if not indoor_attractions.empty:
                            selected_attraction = indoor_attractions.iloc[0].to_dict()
                            # Retirer l’attraction indoor choisie du pool
                            attractions = attractions.drop(indoor_attractions.index[0])
                            a_idx = 0  # reset par sécurité
                        else:
                            # sinon on continue normalement
                            pass
                # Si l'utilisateur a moins de 26 ans, privilégier les musées
                if user_age and user_age < 26:
                    museum_mask = attractions['name'].str.contains('musée', case=False, na=False)
                    museum_attractions = attractions[museum_mask]
                    if not museum_attractions.empty:
                        selected_attraction = museum_attractions.iloc[0].to_dict()
                        attractions = attractions.drop(museum_attractions.index[0])
                        a_idx = 0  # reset par sécurité
                selected_attraction['time_slot'] = time_slot
                recommendations[day_key].append(selected_attraction)
                # Retirer l’attraction utilisée
                attractions = attractions.drop(attractions.index[a_idx]) if a_idx < len(attractions) else attractions
                a_idx = min(a_idx, max(len(attractions) - 1, 0))
    return recommendations
