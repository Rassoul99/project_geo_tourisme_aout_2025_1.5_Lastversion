import os
import streamlit as st
import requests
import folium
from geopy.distance import geodesic
from streamlit_folium import folium_static
import pandas as pd
from datetime import datetime, time, timedelta
from utils.google_api import get_geocode_address, get_nearby_places, get_place_details, google_geolocate
from utils.recommendations import generate_recommendations
from utils.weather import get_weather_forecast
from dotenv import load_dotenv
from fpdf import FPDF
import json
import base64
from pathlib import Path
from utils.chatbot import generate_recommendations_with_chatbot

# Charger les variables d'environnement
load_dotenv()
GOOGLE_PLACES_KEY = os.getenv("GOOGLE_PLACES_KEY")
VIATOR_API_KEY = os.getenv("VIATOR_API_KEY")
OPENWEATHERMAP_KEY = os.getenv("OPENWEATHERMAP_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# --- Fichier pour sauvegarder les préférences ---
PREF_FILE = "user_preferences.json"
FAVORITES_FILE = "favorite_itineraries.json"

def load_preferences():
    if os.path.exists(PREF_FILE):
        with open(PREF_FILE, "r") as f:
            return json.load(f)
    return {}

def save_preferences(prefs):
    with open(PREF_FILE, "w") as f:
        json.dump(prefs, f)

def load_favorites():
    if os.path.exists(FAVORITES_FILE):
        with open(FAVORITES_FILE, "r") as f:
            return json.load(f)
    return []

def save_favorites(favorites):
    with open(FAVORITES_FILE, "w") as f:
        json.dump(favorites, f)

# --- Politique de confidentialité ---
def show_privacy_policy():
    st.markdown("""
    ### 📜 Politique de Confidentialité et RGPD
    La protection de vos données personnelles est une priorité.
    Cette politique décrit comment nous collectons et utilisons vos informations.
    **1. Responsable du traitement**
    📧 [geotourisme25@gmail.com]
    **2. Données collectées**
    - Adresse IP et informations techniques
    - Localisation approximative (si autorisée)
    - Préférences de voyage fournies volontairement
    **3. Base légale**
    - Consentement (cookies)
    - Exécution du contrat
    - Intérêt légitime (amélioration UX)
    **4. Droits RGPD**
    - Accès, rectification, suppression
    - Limitation du traitement
    - Opposition
    - Portabilité
    - Réclamation auprès de la CNIL
    Contact : [geotourisme25@gmail.com]
    **5. Durée de conservation**
    - Données compte : 2 ans après dernière activité
    - Cookies : 13 mois max
    **6. Cookies**
    - Nécessaires → obligatoires
    - Analytiques/marketing → optionnels
    **7. Sécurité**
    Des mesures techniques et organisationnelles protègent vos données.
    **8. Modifications**
    Cette politique peut être mise à jour. Les changements seront publiés ici.
    """)

# --- Popup GDPR (modal si dispo, sinon container) ---
def show_gdpr_popup():
    prefs = load_preferences()
    if not prefs.get("gdpr_accepted", False):
        if hasattr(st, "modal"):
            modal_context = st.modal("📜 Politique de Confidentialité et RGPD")
        else:
            modal_context = st.container()
        with modal_context:
            st.write("Nous utilisons des cookies et collectons certaines données pour améliorer votre expérience.")
            st.write("Veuillez lire et accepter notre politique pour continuer :")
            with st.expander("🔎 Voir la politique complète"):
                show_privacy_policy()
            st.markdown("**Préférences cookies :**")
            analytics = st.checkbox("J'accepte les cookies analytiques (optionnel)", value=False)
            st.info("✅ L'acceptation des conditions essentielles est obligatoire pour utiliser l'application.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Accepter et continuer"):
                    prefs["gdpr_accepted"] = True
                    prefs["analytics_cookies"] = analytics
                    save_preferences(prefs)
                    st.session_state.gdpr_accepted = True
                    st.rerun()
            with col2:
                if st.button("❌ Refuser"):
                    st.error("Vous devez accepter les conditions essentielles pour utiliser cette application.")
                    st.stop()
        st.stop()
    else:
        # Mettre à jour session_state si le fichier JSON contient déjà les infos
        st.session_state.gdpr_accepted = True
        st.session_state.analytics_cookies = prefs.get("analytics_cookies", False)
    return True

# --- Page paramètres > confidentialité ---
def privacy_settings_page():
    st.subheader("⚙️ Paramètres de Confidentialité")
    st.write("Vous pouvez modifier vos préférences à tout moment ci-dessous 👇")
    prefs = load_preferences()
    if "analytics_cookies" not in prefs:
        prefs["analytics_cookies"] = False
    analytics_pref = st.checkbox(
        "J'accepte les cookies analytiques (optionnel)",
        value=prefs["analytics_cookies"]
    )
    if analytics_pref != prefs["analytics_cookies"]:
        prefs["analytics_cookies"] = analytics_pref
        save_preferences(prefs)
        st.success("✅ Vos préférences ont été mises à jour.")
    with st.expander("📜 Voir la politique de confidentialité complète"):
        show_privacy_policy()

def about_page():
    st.title("ℹ️ À propos")
    st.markdown("""
    **Bienvenue sur Smart Travel Planner, votre assistant de voyage intelligent.**
    Notre application vous aide à planifier votre voyage en vous proposant des itinéraires optimisés, des recommandations personnalisées et des conseils basés sur la météo.
    """)
    st.markdown("🌍 **Notre mission :** Rendre la planification de voyage simple et accessible à tous.")
    st.markdown("📧 **Contact :** [geotourisme25@gmail.com](mailto:geotourisme25@gmail.com)")

def how_it_works_page():
    st.title("❓ Comment ça marche")
    st.markdown("""
    **1. Choisissez votre destination :**
    - Entrez la ville et le pays où vous souhaitez vous rendre.
    """)
    st.markdown("""
    **2. Définissez vos préférences :**
    - Sélectionnez les types de lieux que vous souhaitez visiter.
    - Ajoutez votre âge pour des recommandations personnalisées (ex: musées gratuits pour les moins de 26 ans).
    - Choisissez le rayon de recherche et vos préférences horaires.
    """)
    st.markdown("""
    **3. Lancez la recherche :**
    - Cliquez sur le bouton 'Rechercher' pour obtenir des recommandations personnalisées.
    """)
    st.markdown("""
    **4. Explorez les résultats :**
    - Consultez les itinéraires optimisés et les recommandations pour chaque jour de votre séjour.
    """)
    st.markdown("""
    **5. Téléchargez votre itinéraire :**
    - Vous pouvez télécharger votre itinéraire au format PDF pour un accès hors ligne.
    """)

def favorites_page():
    st.title("⭐ Itinéraires Favoris")
    favorites = load_favorites()
    if not favorites:
        st.info("Aucun itinéraire enregistré en favoris.")
    else:
        for i, fav in enumerate(favorites):
            with st.expander(f"📅 {fav['title']}"):
                st.markdown(f"**Destination :** {fav['destination']}")
                st.markdown(f"**Date :** {fav['date']}")
                if st.button(f"Supprimer", key=f"delete_{i}"):
                    favorites.pop(i)
                    save_favorites(favorites)
                    st.rerun()
    st.markdown("---")
    st.subheader("Ajouter aux favoris")
    if 'recommendations' in st.session_state and 'current_weather' in st.session_state:
        if st.button("Ajouter l'itinéraire actuel aux favoris"):
            new_fav = {
                "title": f"Itinéraire pour {st.session_state.get('city', 'Ma Destination')} - {datetime.today().strftime('%Y-%m-%d')}",
                "destination": st.session_state.get('city', 'Ma Destination'),
                "date": datetime.today().strftime("%Y-%m-%d"),
                "recommendations": st.session_state['recommendations'],
                "weather": st.session_state['current_weather']
            }
            favorites.append(new_fav)
            save_favorites(favorites)
            st.success("Itinéraire ajouté aux favoris !")

def chatbot_page():
    st.title("🤖 Chatbot de Recommandations")
    st.markdown("""
    **Instructions :**
    - Écrivez votre propre prompt pour interagir avec le chatbot.
    - Incluez des détails sur votre voyage, comme la date de début, la ville, et vos préférences.
    - Exemple de prompt : "Je vais à Paris à partir du 15 octobre 2025. Quels sont les événements et activités recommandés pour un séjour de 3 jours ?"
    """)
    user_input = st.text_area("Quelles sont vos préférences pour le voyage ?", value="Je vais à Dakar à partir du 15 octobre 2025. Quels sont les événements et activités recommandés pour un séjour de 3 jours ?")
    if st.button("Obtenir des Recommandations"):
        with st.spinner("Génération des recommandations..."):
            try:
                recommendations = generate_recommendations_with_chatbot(user_input)
                st.write("Recommandations:", recommendations["recommendations"])
                st.write("Événements:", recommendations["events"])
            except Exception as e:
                st.error(f"Erreur lors de la génération des recommandations: {e}")

# ---------- Utilitaires locaux ----------
def _normalize_type_for_display(google_types):
    if not google_types:
        return None
    if 'lodging' in google_types:
        return 'hotel'
    if 'restaurant' in google_types:
        return 'restaurant'
    if 'tourist_attraction' in google_types:
        return 'tourist_attraction'
    return google_types[0]

def _build_photo_url(place):
    photo_ref = None
    if place.get('photos'):
        photo_ref = place['photos'][0].get('photo_reference')
    if not photo_ref and place.get('details', {}).get('photos'):
        photo_ref = place['details']['photos'][0].get('photo_reference')
    if photo_ref and GOOGLE_PLACES_KEY:
        return f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={photo_ref}&key={GOOGLE_PLACES_KEY}"
    return None

def get_price_level_description(price_level):
    if price_level == 0:
        return "Économique"
    elif price_level == 1:
        return "Modéré"
    elif price_level == 2:
        return "Cher"
    elif price_level == 3:
        return "Très cher"
    elif price_level == 4:
        return "Luxe"
    else:
        return "Non spécifié"

def fetch_weather_forecast(lat, lng, days):
    api_key = os.getenv("OPENWEATHERMAP_KEY")
    if not api_key:
        return None
    weather_forecasts = {}
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lng}&appid={api_key}&units=metric&lang=fr"
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get('cod') == '200':
            for forecast in data.get('list', []):
                date = datetime.fromtimestamp(forecast.get('dt')).strftime("%Y-%m-%d")
                if date not in weather_forecasts:
                    weather_forecasts[date] = {
                        'temp': round(forecast['main']['temp']),
                        'description': forecast['weather'][0]['description'].capitalize(),
                        'icon': forecast['weather'][0].get('icon')
                    }
            existing_dates = sorted(weather_forecasts.keys())
            for day in range(days):
                date = (datetime.now() + timedelta(days=day)).strftime("%Y-%m-%d")
                if date not in weather_forecasts and existing_dates:
                    weather_forecasts[date] = weather_forecasts[existing_dates[-1]]
    except Exception as e:
        print(f"Erreur réseau: {e}")
    return weather_forecasts

def get_location_name(lat, lng):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lng}"
        response = requests.get(url, timeout=10)
        data = response.json()
        address = data.get('address', {})
        # Ajout de fallback sur d'autres champs
        city = address.get('city') or address.get('town') or address.get('village') or address.get('hamlet') or address.get('municipality') or address.get('county')
        state = address.get('state', '')
        country = address.get('country', '')
        road = address.get('road', '')
        suburb = address.get('suburb', '')
        # Debug
        print(f"DEBUG address: {address}")
        if city and country:
            return f"{city}, {country}"
        elif suburb and country:
            return f"{suburb}, {country}"
        elif road and country:
            return f"{road}, {country}"
        elif state and country:
            return f"{state}, {country}"
        elif country:
            return country
        else:
            return "Lieu inconnu"
    except Exception as e:
        print(f"Erreur lors de la récupération du nom du lieu: {e}")
        return "Lieu inconnu"

# --- Application principale ---
if show_gdpr_popup():
    st.set_page_config(
        page_title="🌍 Smart Travel Planner",
        page_icon="🌍",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    # Sidebar navigation
    st.sidebar.title("Menu")
    page = st.sidebar.radio("Navigation", ["🏠 Accueil", "🤖 Chatbot", "⚙️ Confidentialité", "ℹ️ À propos", "❓ Comment ça marche", "⭐ Favoris"])
    # CSS pour améliorer l'interface
    st.markdown("""
    <style>
        .stButton > button {
            background-color: #4CAF50;
            color: white;
        }
        .stSelectbox, .stTextInput, .stSlider, .stNumberInput {
            margin-bottom: 1rem;
        }
        .icon {
            font-size: 1.5em;
            margin-right: 0.5em;
        }
        @media (max-width: 768px) {
            .stButton > button {
                width: 100%;
            }
        }
    </style>
    """, unsafe_allow_html=True)
    if page == "🏠 Accueil":
        st.title("🌍 Smart Travel Planner")
        st.markdown("Planifiez votre voyage idéal avec des recommandations personnalisées basées sur vos préférences.")
        # Détection de position par défaut
        if 'start_location' not in st.session_state:
            try:
                response = requests.get('https://ipinfo.io/json', timeout=5)
                data = response.json()
                if 'loc' in data:
                    lat, lng = data['loc'].split(',')
                    st.session_state['start_location'] = (float(lat), float(lng))
                if os.getenv("GOOGLE_PLACES_KEY"):
                    g_loc = google_geolocate()
                    if g_loc:
                        st.session_state['start_location'] = (g_loc['lat'], g_loc['lng'])
                if 'start_location' in st.session_state:
                    lat, lng = st.session_state['start_location']
                    weather = get_weather_forecast(lat, lng)
                    if weather:
                        st.session_state['current_weather'] = {datetime.today().strftime("%Y-%m-%d"): weather}
                    st.success(f"📍 Position détectée automatiquement: {lat:.5f}, {lng:.5f}")
                else:
                    st.error("Impossible de détecter votre position par défaut.")
            except Exception as e:
                st.error(f"Erreur de détection automatique: {e}")
        with st.sidebar:
            st.header("⚙️ Filtres")
            country = st.text_input("🌎 Pays", "France")
            city = st.text_input("🏙️ Ville", "Paris")
            start_date = st.date_input("📅 Date de début", datetime.today())
            stay_duration = st.number_input("📅 Durée du séjour (jours)", min_value=1, value=3, key="stay_duration")
            age = st.number_input("👤 Âge", min_value=0, max_value=120, value=25, key="age")
            # Personnalisation
            st.subheader("🍽️ Types de cuisine préférés")
            cuisine_types = st.multiselect(
                "Sélectionnez vos cuisines préférées",
                ["Française", "Italienne", "Chinoise", "Japonaise", "Indienne", "Mexicaine", "Autre"],
                default=["Française", "Italienne"]
            )
            st.subheader("🎭 Activités préférées")
            activity_types = st.multiselect(
                "Sélectionnez vos activités préférées",
                ["Musées", "Parcs", "Shopping", "Randonnée", "Sports", "Culture"],
                default=["Musées", "Culture"]
            )
            st.subheader("📍 Types de lieux")
            poi_types = st.multiselect(
                "Sélectionnez vos types de lieux",
                ["restaurant", "hotel", "tourist_attraction"],
                default=["restaurant", "hotel", "tourist_attraction"]
            )
            st.subheader("🎟️ Catégories d'événements")
            event_categories = st.multiselect(
                "Sélectionnez vos catégories d'événements préférées",
                ["concerts", "sports", "festivals", "conferences", "expositions", "other"],
                default=["concerts", "sports", "festivals", "conferences", "expositions"]
            )
            radius = st.slider("📏 Rayon de recherche (mètres)", 100, 5000, 2000, key="radius")
            time_preferences = st.multiselect(
                "⏰ Préférences horaires",
                ["Matin (8h-12h)", "Midi (12h-14h)", "Soir (18h-22h)"],
                default=["Midi (12h-14h)", "Soir (18h-22h)"]
            )
            min_rating = st.slider("⭐ Note minimale", 1.0, 5.0, 4.0, 0.1)
            detect_location = st.button("📍 Détecter ma position")
        # Détection de la position à la demande
        if detect_location:
            try:
                lat_lng = None
                response = requests.get('https://ipinfo.io/json', timeout=5)
                data = response.json()
                if 'loc' in data:
                    lat, lng = data['loc'].split(',')
                    lat_lng = (float(lat), float(lng))
                g_loc = google_geolocate()
                if g_loc:
                    lat_lng = (g_loc['lat'], g_loc['lng'])
                if lat_lng:
                    st.session_state['start_location'] = lat_lng
                    st.success(f"Position détectée: {lat_lng[0]:.5f}, {lat_lng[1]:.5f}")
                    weather = get_weather_forecast(lat_lng[0], lat_lng[1])
                    if weather:
                        st.session_state['current_weather'] = {datetime.today().strftime("%Y-%m-%d"): weather}
                else:
                    st.error("Impossible de détecter votre position.")
            except Exception as e:
                st.error(f"Erreur de détection: {e}")
        # Fonction pour générer un PDF
        def generate_pdf(recommendations, weather_forecasts, start_date, stay_duration, city):
            pdf = FPDF()
            try:
                pdf.add_font('DejaVu', '', 'DejaVuSansCondensed.ttf', uni=True)
                pdf.set_font('DejaVu', '', 12)
            except:
                pdf.set_font("Arial", size=12)
            pdf.add_page()
            for day_num in range(1, stay_duration + 1):
                day_key = f"Day {day_num}"
                day_date = (start_date + timedelta(days=day_num - 1)).strftime("%Y-%m-%d")
                day_pois = recommendations.get(day_key, [])
                weather_info = weather_forecasts.get(day_date, {})
                weather_description = weather_info.get('description', 'Non disponible')
                temp = weather_info.get('temp', '-')
                clean_day_text = f"Jour {day_num} ({day_date}): Météo prévue - Température: {temp}°C, Conditions: {weather_description}".encode('latin1', 'ignore').decode('latin1')
                pdf.cell(200, 10, txt=clean_day_text, ln=True, align='C')
                pdf.cell(200, 10, txt="Hôtel:", ln=True)
                hotels = [poi for poi in day_pois if poi.get('type') == 'hotel']
                for hotel in hotels:
                    clean_text = f"Nom: {hotel['name']}, Note: {hotel.get('rating','N/A')}⭐".encode('latin1', 'ignore').decode('latin1')
                    pdf.cell(200, 10, txt=clean_text, ln=True)
                pdf.cell(200, 10, txt="Activités:", ln=True)
                for poi in day_pois:
                    if poi.get('type') != 'hotel' and poi.get('type') != 'event':
                        activity_text = f"Activité: {poi['name']} ({poi.get('type', '')})"
                        clean_activity_text = activity_text.encode('latin1', 'ignore').decode('latin1')
                        pdf.cell(200, 10, txt=clean_activity_text, ln=True)
                        if 'time_slot' in poi:
                            clean_time_slot = str(poi['time_slot']).encode('latin1', 'ignore').decode('latin1')
                            pdf.cell(200, 10, txt=f"Créneau: {clean_time_slot}", ln=True)
                pdf.cell(200, 10, txt="Événements:", ln=True)
                for poi in day_pois:
                    if poi.get('type') == 'event':
                        event_text = f"Événement: {poi['name']} ({poi.get('category', '')})"
                        clean_event_text = event_text.encode('latin1', 'ignore').decode('latin1')
                        pdf.cell(200, 10, txt=clean_event_text, ln=True)
                        if 'start_local' in poi:
                            clean_start_local = str(poi['start_local']).encode('latin1', 'ignore').decode('latin1')
                            pdf.cell(200, 10, txt=f"Date: {clean_start_local}", ln=True)
            byte_array_output = pdf.output(dest='S')
            if isinstance(byte_array_output, bytearray):
                byte_array_output = bytes(byte_array_output)
            return byte_array_output
        # Fonction pour récupérer les événements
        def fetch_events(category=None, country="FR", city=None, limit=5):
            ACCESS_TOKEN = "yCdaGN2Hw12zeYW0DfalpiUmYlmoFYySpKjNe-iS"
            BASE_URL = "https://api.predicthq.com/v1"
            HEADERS = {
                "Authorization": f"Bearer {ACCESS_TOKEN}",
                "Accept": "application/json"
            }
            url = f"{BASE_URL}/events/"
            params = {
                "country": country,
                "limit": limit,
                "sort": "start",
                "start.gte": datetime.now().isoformat(),
                "location": city
            }
            if category:
                params["category"] = category
            r = requests.get(url, headers=HEADERS, params=params)
            print(f"GET {r.url} -> {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                for event in data.get('results', []):
                    # 1. Adresse dans geo.address
                    address = event.get('geo', {}).get('address', {}).get('formatted_address')
                    # 2. Adresse dans les entités de type venue
                    if not address and 'entities' in event:
                        for ent in event['entities']:
                            if ent.get('type') == 'venue' and ent.get('formatted_address'):
                                address = ent['formatted_address']
                                break
                    # 3. Fallback: reverse geocoding
                    if not address and 'location' in event and isinstance(event['location'], list) and len(event['location']) == 2:
                        lat, lng = event['location'][1], event['location'][0]
                        address = get_location_name(lat, lng)
                    event['location_name'] = address if address else "Lieu inconnu"
                return data
            else:
                print(r.text)
                return None
        # Recherche
        if st.button("🔍 Rechercher"):
            with st.spinner("Recherche des meilleurs lieux..."):
                try:
                    location = get_geocode_address(f"{city}, {country}")
                    if not location:
                        st.error(f"Impossible de trouver {city}. Essayez une autre ville.")
                        st.stop()
                    lat, lng = location['lat'], location['lng']
                    st.session_state['start_location'] = (lat, lng)
                    st.session_state['city'] = city
                    st.write(f"Coordonnées pour {city}: {lat}, {lng}")
                    # Récupérer la météo pour chaque jour du séjour
                    weather_forecasts = fetch_weather_forecast(lat, lng, stay_duration)
                    if weather_forecasts:
                        st.session_state['current_weather'] = weather_forecasts
                    all_pois = []
                    for poi_type in poi_types:
                        g_type = 'lodging' if poi_type == 'hotel' else poi_type
                        pois = get_nearby_places((lat, lng), radius, g_type)
                        for poi in pois:
                            details = get_place_details(poi.get('place_id'))
                            place = {
                                'name': poi.get('name') or details.get('name'),
                                'place_id': poi.get('place_id'),
                                'google_types': details.get('types') or poi.get('types', []),
                                'address': details.get('vicinity') or details.get('formatted_address') or poi.get('vicinity'),
                                'latitude': details.get('geometry', {}).get('location', {}).get('lat') or poi.get('geometry', {}).get('location', {}).get('lat'),
                                'longitude': details.get('geometry', {}).get('location', {}).get('lng') or poi.get('geometry', {}).get('location', {}).get('lng'),
                                'rating': details.get('rating', poi.get('rating', 0)),
                                'user_ratings_total': details.get('user_ratings_total', poi.get('user_ratings_total', 0)),
                                'price_level': details.get('price_level', poi.get('price_level', 0)),
                                'reviews': details.get('reviews', []),
                                'website': details.get('website'),
                                'formatted_phone_number': details.get('formatted_phone_number', details.get('international_phone_number')),
                                'opening_hours_raw': details.get('opening_hours', {}),
                                'details': details,
                                'photo_url': None,
                                'description': details.get('editorial_summary', {}).get('overview', '') if details.get('editorial_summary') else ''
                            }
                            place['type'] = _normalize_type_for_display(place['google_types'])
                            place['photo_url'] = _build_photo_url(place)
                            if place['latitude'] is not None and place['longitude'] is not None:
                                place['distance'] = geodesic((lat, lng), (place['latitude'], place['longitude'])).meters
                            else:
                                place['distance'] = None
                            opening_hours = place['opening_hours_raw'] or {}
                            place['opening_hours'] = opening_hours.get('weekday_text', []) if isinstance(opening_hours, dict) else []
                            place['is_open_now'] = opening_hours.get('open_now') if isinstance(opening_hours, dict) else None
                            if place['type'] in {"hotel", "restaurant", "tourist_attraction"}:
                                all_pois.append(place)
                    if not all_pois:
                        st.error("Aucun lieu trouvé. Essayez d'élargir le rayon.")
                        st.stop()
                    pois_df = pd.DataFrame(all_pois)
                    st.session_state['pois'] = pois_df
                    # Récupérer les événements
                    events = fetch_events(category=event_categories[0] if event_categories else None, country=country, city=city, limit=5)
                    if events:
                        st.session_state['events'] = events
                    recommendations = generate_recommendations(
                        pois_df,
                        min_rating=min_rating,
                        stay_duration=stay_duration,
                        time_preferences=time_preferences,
                        weather=st.session_state['current_weather'],
                        user_age=age,
                        events=events
                    )
                    st.session_state['recommendations'] = recommendations
                except Exception as e:
                    st.error(f"Erreur lors de la recherche: {e}")
        # Affichage des résultats
        if 'recommendations' in st.session_state and 'current_weather' in st.session_state:
            tab1, tab2, tab3, tab4 = st.tabs(["Carte", "Résumé du voyage", "Événements", "🤖 Chatbot"])
            with tab1:
                st.header("🏆 Itinéraire Optimisé")
                m = folium.Map(location=st.session_state['start_location'], zoom_start=14)
                folium.Marker(
                    location=st.session_state['start_location'],
                    popup='Votre position',
                    icon=folium.Icon(color='red', icon='home')
                ).add_to(m)
                # Couleurs utilisées pour chaque jour
                colors = ['blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige']
                legend_html = """
                <div style="position: fixed; bottom: 50px; left: 50px; width: 200px; border:2px solid grey; z-index:9999; font-size:14px; background-color:white; padding:8px;">
                <b>Légende:</b><br>
                """
                for day_num in range(1, stay_duration + 1):
                    color = colors[day_num % len(colors)]
                    legend_html += f'<i class="fa fa-map-marker" style="color:{color}"></i> Jour {day_num}<br>'
                legend_html += '<i class="fa fa-calendar" style="color:orange"></i> Événement<br>'
                legend_html += '<i class="fa fa-home" style="color:red"></i> Votre position<br>'
                legend_html += "</div>"
                m.get_root().html.add_child(folium.Element(legend_html))
                day_summaries = []
                previous_location = st.session_state['start_location']
                for day_num, (day, day_pois) in enumerate(st.session_state['recommendations'].items(), 1):
                    color = colors[day_num % len(colors)]
                    day_summary = {"day": day_num, "activities": [], "hotel": None, "events": []}
                    seen_places = set()
                    for poi in day_pois:
                        if poi.get('place_id') and poi['place_id'] in seen_places:
                            continue
                        if poi.get('place_id'):
                            seen_places.add(poi['place_id'])
                        icon_type = {
                            'hotel': 'bed',
                            'restaurant': 'utensils',
                            'tourist_attraction': 'star',
                            'event': 'calendar'
                        }.get(poi.get('type'), 'info-sign')
                        folium.Marker(
                            location=[poi['latitude'], poi['longitude']] if poi.get('latitude') and poi.get('longitude') else st.session_state['start_location'],
                            popup=f"""
                            <div style="width: 220px;">
                                <b>{poi['name']}</b><br>
                                Type: {poi.get('type','-')}<br>
                                {f"Note: {poi.get('rating','-')}/5⭐<br>" if poi.get('rating') else ""}
                                {f"Adresse: {poi.get('address', 'Non renseignée')}<br>" if poi.get('address') else ""}
                                {f"Niveau de prix: {get_price_level_description(poi.get('price_level', 0))}<br>" if poi.get('price_level') else ""}
                                {f"Horaire: {poi.get('time_slot', 'Toute la journée')}<br>" if poi.get('time_slot') else ""}
                                {f"Description: {poi.get('description', '')}<br>" if poi.get('description') else ""}
                                {f"<img src='{poi['photo_url']}' width='100%'><br>" if poi.get('photo_url') else ""}
                                {f"<a href='{poi['website']}' target='_blank'>Site web</a><br>" if poi.get('website') else ''}
                            </div>
                            """,
                            icon=folium.Icon(color=color if poi.get('type') != 'event' else 'orange', icon=icon_type, prefix='fa')
                        ).add_to(m)
                        if previous_location and poi.get('latitude') and poi.get('longitude'):
                            folium.PolyLine(
                                locations=[previous_location, [poi['latitude'], poi['longitude']]],
                                color=color,
                                weight=2,
                                opacity=0.7
                            ).add_to(m)
                            previous_location = [poi['latitude'], poi['longitude']]
                        if poi.get('type') == 'hotel':
                            day_summary["hotel"] = poi
                        elif poi.get('type') == 'event':
                            day_summary["events"].append(poi)
                        else:
                            day_summary["activities"].append(poi)
                    day_summaries.append(day_summary)
                folium_static(m, width=700, height=500)
            with tab2:
                st.header("Résumé du voyage")
                for summary in day_summaries:
                    date = start_date + timedelta(days=summary['day'] - 1)
                    date_str = date.strftime('%Y-%m-%d')
                    weather_info = st.session_state['current_weather'].get(date_str, {})
                    weather_description = weather_info.get('description', 'Non disponible')
                    temperature = weather_info.get('temp', '-')
                    advice = "Temps idéal pour les activités extérieures"
                    if any(k in weather_description.lower() for k in ["pluie", "orage", "bruine", "neige"]):
                        advice = "Prévoyez un parapluie et privilégiez les activités en intérieur"
                    elif any(k in weather_description.lower() for k in ["vent", "rafale"]):
                        advice = "Évitez les hauteurs exposées et les activités nautiques"
                    st.markdown(f"### 📅 Jour {summary['day']} ({date_str})")
                    st.markdown(f"**🌦️ Météo prévue** : Température: {temperature}°C, Conditions: {weather_description}, Conseil: {advice}")
                    if summary['hotel']:
                        hotel = summary['hotel']
                        rating_stars = "⭐" * int(hotel.get('rating', 0))
                        st.markdown(f"#### 🏨 Hôtel: {hotel.get('name','-')}")
                        st.markdown(f"- Note: {hotel.get('rating','N/A')}/5 {rating_stars}")
                        st.markdown(f"- Niveau de prix: {get_price_level_description(hotel.get('price_level', 0))}")
                        st.markdown(f"- Téléphone: {hotel.get('formatted_phone_number', 'N/A')}")
                        st.markdown(f"- Ouvert maintenant: {'Oui' if hotel.get('is_open_now') else 'Non'}")
                        st.markdown(f"- Adresse: {hotel.get('address','-')}")
                        st.markdown(f"- Description: {hotel.get('description', 'Non spécifiée')}")
                        if hotel.get('photo_url'):
                            st.image(hotel['photo_url'], width=100)
                    st.markdown("#### 🎯 Activités:")
                    for activity in summary['activities']:
                        rating_stars = "⭐" * int(activity.get('rating', 0))
                        st.markdown(f"**{activity.get('name','-')}** ({activity.get('type','-')})")
                        st.markdown(f"- Note: {activity.get('rating','-')}/5 {rating_stars}")
                        st.markdown(f"- Adresse: {activity.get('address','-')}")
                        st.markdown(f"- Horaire: {activity.get('time_slot', 'Toute la journée')}")
                        st.markdown(f"- Niveau de prix: {get_price_level_description(activity.get('price_level', 0))}")
                        st.markdown(f"- Description: {activity.get('description', 'Non spécifiée')}")
                        if activity.get('photo_url'):
                            st.image(activity['photo_url'], width=100)
                    if summary['events']:
                        st.markdown("#### 🎟️ Événements:")
                        for event in summary['events']:
                            st.markdown(f"**{event.get('name', 'Événement sans titre')}** ({event.get('category', 'Non spécifiée')})")
                            st.markdown(f"- Date: {event.get('start_local', 'Non spécifiée')}")
                            st.markdown(f"- Lieu: {event.get('location_name', 'Non spécifié')}")
                            st.markdown(f"- Description: {event.get('description', 'Non spécifiée')}")
            with tab3:
                st.header("🎟️ Événements (pas nécessairement à proximité)")
                if 'events' in st.session_state:
                    events = st.session_state['events'].get('results', [])
                    if events:
                        for event in events:
                            st.markdown(f"**{event.get('title', 'Événement sans titre')}**")
                            st.markdown(f"- Catégorie: {event.get('category', 'Non spécifiée')}")
                            st.markdown(f"- Date: {event.get('start_local', 'Non spécifiée')}")
                            st.markdown(f"- Lieu: {event.get('location_name', 'Non spécifié')}")
                            st.markdown(f"- Coordonnées: {event.get('location', 'Non spécifié')}")
                            st.markdown(f"- Description: {event.get('description', 'Non spécifiée')}")
                    else:
                        st.info("Aucun événement trouvé.")
                else:
                    st.info("Aucun événement trouvé.")
            with tab4:
                chatbot_page()
            st.download_button(
                label="Télécharger l'itinéraire (PDF)",
                data=generate_pdf(st.session_state['recommendations'], st.session_state['current_weather'], start_date, stay_duration, city),
                file_name=f"itinerary_{city}.pdf",
                mime="application/pdf"
            )
    elif page == "🤖 Chatbot":
        chatbot_page()
    elif page == "⚙️ Confidentialité":
        privacy_settings_page()
        st.markdown("---")
    elif page == "ℹ️ À propos":
        about_page()
    elif page == "❓ Comment ça marche":
        how_it_works_page()
    elif page == "⭐ Favoris":
        favorites_page()
    if 'recommendations' in st.session_state:
        st.markdown("---")
        st.markdown("""
        **📋 Voulez-vous nous aider à améliorer ?**
        Nous apprécions vos retours pour améliorer notre application.
        Veuillez remplir ce [formulaire Google Form](https://forms.gle/R7Z2QrwRig9uuSrk8) pour nous faire part de vos suggestions et de votre expérience.
        """)
