# save note 5/5 ***** + prix_level :

import os
import streamlit as st
import requests
import folium
from geopy.distance import geodesic
from streamlit_folium import folium_static
import pandas as pd
from datetime import datetime, time
from utils.google_api import get_geocode_address, get_nearby_places, get_place_details, google_geolocate
from utils.recommendations import generate_recommendations
from utils.weather import get_weather_forecast
from dotenv import load_dotenv
from fpdf import FPDF

# Charger les variables d'environnement
load_dotenv()
GOOGLE_PLACES_KEY = os.getenv("GOOGLE_PLACES_KEY")
VIATOR_API_KEY = os.getenv("VIATOR_API_KEY", "8cd8a095-d7c6-47ea-a0e7-9afacc40a0c5")
OPENWEATHERMAP_KEY = os.getenv("OPENWEATHERMAP_KEY")

import streamlit as st
import json
import os

# --- Fichier pour sauvegarder les préférences ---
PREF_FILE = "user_preferences.json"

def load_preferences():
    if os.path.exists(PREF_FILE):
        with open(PREF_FILE, "r") as f:
            return json.load(f)
    return {}

def save_preferences(prefs):
    with open(PREF_FILE, "w") as f:
        json.dump(prefs, f)

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

# ---------- Utilitaires locaux ----------
def _normalize_type_for_display(google_types):
    """
    Normalize Google place types to your app types.
    - 'lodging' -> 'hotel'  # FIX: clé pour afficher les hôtels
    - 'restaurant' -> 'restaurant'
    - 'tourist_attraction' -> 'tourist_attraction'
    """
    if not google_types:
        return None
    if 'lodging' in google_types:
        return 'hotel'
    if 'restaurant' in google_types:
        return 'restaurant'
    if 'tourist_attraction' in google_types:
        return 'tourist_attraction'
    # fallback: premier type Google
    return google_types[0]

def _build_photo_url(place):
    # FIX: utiliser photo depuis details OU depuis search quand details n’a rien
    photo_ref = None
    if place.get('photos'):
        photo_ref = place['photos'][0].get('photo_reference')
    if not photo_ref and place.get('details', {}).get('photos'):
        photo_ref = place['details']['photos'][0].get('photo_reference')
    if photo_ref and GOOGLE_PLACES_KEY:
        return f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={photo_ref}&key={GOOGLE_PLACES_KEY}"
    return None

def get_price_level_description(price_level):
    """
    Retourne une description lisible pour le niveau de prix.
    """
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
    page = st.sidebar.radio("Navigation", ["🏠 Accueil", "⚙️ Confidentialité"])
    if page == "🏠 Accueil":
        # Titre et description
        st.title("🌍 Smart Travel Planner")
        st.markdown("""
        Planifiez votre voyage idéal avec des recommandations personnalisées basées sur les avis et les horaires d'ouverture.
        """)
        st.markdown("**💡 Conseils:**")
        st.markdown("- Utilisez les filtres pour affiner vos résultats et n’hésitez pas à élargir le rayon de recherche si nécessaire, afin d’obtenir plus de propositions d’activités.")
        st.markdown("- Les itinéraires sont optimisés en fonction de la météo et de vos préférences")
        # 👉 Ajouter ton code principal ici
    elif page == "⚙️ Confidentialité":
        privacy_settings_page()
        st.markdown("---")
    # Ajoutez ce CSS pour styliser le bouton
    st.markdown("""
    <style>
        .stButton > button {
            background-color: green;
            color: white;
        }
    </style>
    """, unsafe_allow_html=True)

    # ---------- Détection de position par défaut ----------
    if 'start_location' not in st.session_state:
        # FIX: stratégie en cascade: ipinfo -> Google Geolocation (si clé) -> message
        try:
            # 1) IP approx
            response = requests.get('https://ipinfo.io/json', timeout=5)
            data = response.json()
            if 'loc' in data:
                lat, lng = data['loc'].split(',')
                st.session_state['start_location'] = (float(lat), float(lng))
            # 2) Google Geolocation (plus précis si dispo)
            if os.getenv("GOOGLE_PLACES_KEY"):
                g_loc = google_geolocate()
                if g_loc:
                    st.session_state['start_location'] = (g_loc['lat'], g_loc['lng'])
            if 'start_location' in st.session_state:
                lat, lng = st.session_state['start_location']
                st.session_state['current_weather'] = get_weather_forecast(lat, lng)
                st.success(f"Position détectée automatiquement: {lat:.5f}, {lng:.5f}")
            else:
                st.error("Impossible de détecter votre position par défaut.")
        except Exception as e:
            st.error(f"Erreur de détection automatique: {e}")

    # Sidebar pour les filtres
    with st.sidebar:
        st.header("⚙️ Filtres")
        country = st.text_input("Pays", "France")
        city = st.text_input("Ville", "Paris")
        stay_duration = st.number_input("Durée du séjour (jours)", min_value=1, value=3)
        poi_types = st.multiselect(
            "Types de lieux",
            ["restaurant", "hotel", "tourist_attraction"],
            default=["restaurant", "hotel", "tourist_attraction"]
        )
        radius = st.slider("Rayon de recherche (mètres)", 100, 5000, 100)
        time_preferences = st.multiselect(
            "Préférences horaires",
            ["Matin (8h-12h)", "Midi (12h-14h)", "Soir (18h-22h)"],
            default=["Matin (8h-12h)", "Midi (12h-14h)", "Soir (18h-22h)"]
        )
        min_rating = st.slider("Note minimale", 1.0, 5.0, 4.0, 0.1)
        detect_location = st.button("📍 Détecter ma position")

    # Détection de la position à la demande
    if detect_location:
        try:
            # IP approx
            lat_lng = None
            response = requests.get('https://ipinfo.io/json', timeout=5)
            data = response.json()
            if 'loc' in data:
                lat, lng = data['loc'].split(',')
                lat_lng = (float(lat), float(lng))
            # Google Geolocation si possible
            g_loc = google_geolocate()
            if g_loc:
                lat_lng = (g_loc['lat'], g_loc['lng'])
            if lat_lng:
                st.session_state['start_location'] = lat_lng
                st.success(f"Position détectée: {lat_lng[0]:.5f}, {lat_lng[1]:.5f}")
                st.session_state['current_weather'] = get_weather_forecast(lat_lng[0], lat_lng[1])
            else:
                st.error("Impossible de détecter votre position.")
        except Exception as e:
            st.error(f"Erreur de détection: {e}")

    # Fonction pour générer un PDF
    def generate_pdf(recommendations):
        pdf = FPDF()
        try:
            pdf.add_font('DejaVu', '', 'DejaVuSansCondensed.ttf', uni=True)
            pdf.set_font('DejaVu', '', 12)
        except:
            pdf.set_font("Arial", size=12)
        pdf.add_page()
        for day, day_pois in recommendations.items():
            clean_day_text = day.encode('latin1', 'ignore').decode('latin1')
            pdf.cell(200, 10, txt=clean_day_text, ln=True, align='C')
            pdf.cell(200, 10, txt="Hôtel:", ln=True)
            hotels = [poi for poi in day_pois if poi.get('type') == 'hotel']
            for hotel in hotels:
                clean_text = f"Nom: {hotel['name']}, Note: {hotel.get('rating','N/A')}⭐".encode('latin1', 'ignore').decode('latin1')
                pdf.cell(200, 10, txt=clean_text, ln=True)
                # Ajout des étoiles en fonction de la note
            pdf.cell(200, 10, txt="Activités:", ln=True)
            for poi in day_pois:
                if poi.get('type') != 'hotel':
                    activity_text = f"Activité: {poi['name']} ({poi.get('type', '')})"
                    clean_activity_text = activity_text.encode('latin1', 'ignore').decode('latin1')
                    pdf.cell(200, 10, txt=clean_activity_text, ln=True)
                    if 'time_slot' in poi:
                        clean_time_slot = str(poi['time_slot']).encode('latin1', 'ignore').decode('latin1')
                        pdf.cell(200, 10, txt=f"Créneau: {clean_time_slot}", ln=True)
        byte_array_output = pdf.output(dest='S')
        if isinstance(byte_array_output, bytearray):
            byte_array_output = bytes(byte_array_output)
        return byte_array_output

    # Recherche
    if st.button("Rechercher"):
        with st.spinner("Recherche des meilleurs lieux..."):
            try:
                location = get_geocode_address(f"{city}, {country}")
                if not location:
                    st.error(f"Impossible de trouver {city}. Essayez une autre ville.")
                    st.stop()
                lat, lng = location['lat'], location['lng']
                st.session_state['start_location'] = (lat, lng)
                st.write(f"Coordonnées pour {city}: {lat}, {lng}")
                st.session_state['current_weather'] = get_weather_forecast(lat, lng)
                all_pois = []
                for poi_type in poi_types:
                    # FIX: conversion 'hotel' -> type Google 'lodging' pour obtenir des hôtels
                    g_type = 'lodging' if poi_type == 'hotel' else poi_type
                    pois = get_nearby_places((lat, lng), radius, g_type)
                    for poi in pois:
                        details = get_place_details(poi.get('place_id'))
                        # Construire un objet "place" enrichi pour extractions homogènes
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
                            'photo_url': None
                        }
                        # Type normalisé
                        place['type'] = _normalize_type_for_display(place['google_types'])
                        # Photo
                        place['photo_url'] = _build_photo_url(place)
                        # Distance
                        if place['latitude'] is not None and place['longitude'] is not None:
                            place['distance'] = geodesic((lat, lng), (place['latitude'], place['longitude'])).meters
                        else:
                            place['distance'] = None
                        # Horaires
                        opening_hours = place['opening_hours_raw'] or {}
                        place['opening_hours'] = opening_hours.get('weekday_text', []) if isinstance(opening_hours, dict) else []
                        place['is_open_now'] = opening_hours.get('open_now') if isinstance(opening_hours, dict) else None
                        # On ne garde que les types qui nous intéressent réellement
                        if place['type'] in {"hotel", "restaurant", "tourist_attraction"}:
                            all_pois.append(place)
                if not all_pois:
                    st.error("Aucun lieu trouvé. Essayez d'élargir le rayon.")
                    st.stop()
                pois_df = pd.DataFrame(all_pois)
                st.session_state['pois'] = pois_df
                recommendations = generate_recommendations(
                    pois_df, min_rating=min_rating, stay_duration=stay_duration, time_preferences=time_preferences,
                    weather=st.session_state['current_weather']
                )
                st.session_state['recommendations'] = recommendations
            except Exception as e:
                st.error(f"Erreur lors de la recherche: {e}")

    # Affichage des résultats
    if 'recommendations' in st.session_state:
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.session_state.get('current_weather'):
                weather = st.session_state['current_weather']
                # FIX: conseil météo plus fiable (pluie/orage/bruine/neige/vent)
                advice = "Temps idéal pour les activités extérieures"
                desc = weather.get('description', '').lower()
                if any(k in desc for k in ["pluie", "orage", "bruine", "neige"]):
                    advice = "Prévoyez un parapluie et privilégiez les activités en intérieur"
                elif any(k in desc for k in ["vent", "rafale"]):
                    advice = "Évitez les hauteurs exposées et les activités nautiques"
                st.markdown(f"""
                ### 🌦️ Météo pour {city.upper()}
                - **Température**: {weather.get('temp','-')}°C
                - **Conditions**: {weather.get('description','-')}
                - **Conseil**: {advice}
                """)
            st.header("🏆 Itinéraire Optimisé")
            m = folium.Map(location=st.session_state['start_location'], zoom_start=14)
            folium.Marker(
                location=st.session_state['start_location'],
                popup='Votre position',
                icon=folium.Icon(color='red', icon='home')
            ).add_to(m)
            legend_html = """
            <div style="position: fixed; bottom: 50px; left: 50px; width: 180px; height: 140px; border:2px solid grey; z-index:9999; font-size:14px; background-color:white; padding:8px;">
            <b>Légende:</b><br>
            <i class="fa fa-map-marker" style="color:blue"></i> Jour 1<br>
            <i class="fa fa-map-marker" style="color:green"></i> Jour 2<br>
            <i class="fa fa-map-marker" style="color:purple"></i> Jour 3<br>
            <i class="fa fa-road" style="color:orange"></i> Trajet
            </div>
            """
            m.get_root().html.add_child(folium.Element(legend_html))
            day_summaries = []
            previous_location = st.session_state['start_location']
            colors = ['blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige']
            for day_num, (day, day_pois) in enumerate(st.session_state['recommendations'].items(), 1):
                color = colors[day_num % len(colors)]
                day_summary = {"day": day_num, "activities": [], "hotel": None}
                seen_places = set()
                for poi in day_pois:
                    if poi['place_id'] in seen_places:
                        continue
                    seen_places.add(poi['place_id'])
                    icon_type = {
                        'hotel': 'bed',
                        'restaurant': 'utensils',
                        'tourist_attraction': 'star'
                    }.get(poi.get('type'), 'info-sign')
                    folium.Marker(
                        location=[poi['latitude'], poi['longitude']],
                        popup=f"""
                        <div style="width: 220px;">
                            <b>{poi['name']}</b><br>
                            Type: {poi.get('type','-')}<br>
                            Note: {poi.get('rating','-')}/5⭐<br>
                            Adresse: {poi.get('address', 'Non renseignée')}<br>
                            Niveau de prix: {get_price_level_description(poi.get('price_level', 0))}<br>
                            {f"<img src='{poi['photo_url']}' width='100%'><br>" if poi.get('photo_url') else ""}
                            {f"<a href='{poi['website']}' target='_blank'>Site web</a><br>" if poi.get('website') else ''}
                        </div>
                        """,
                        icon=folium.Icon(color=color, icon=icon_type, prefix='fa')
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
                    else:
                        day_summary["activities"].append(poi)
                day_summaries.append(day_summary)
            folium_static(m, width=700, height=500)
        with col2:
            st.markdown("### Légende des Jours")
            for day_num in range(1, stay_duration + 1):
                color = colors[day_num % len(colors)]
                st.markdown(f"- Jour {day_num}: <span style='color:{color}'>■</span>", unsafe_allow_html=True)
        st.header("📝 Résumé de votre voyage")

        # Légende des niveaux de prix
        # st.markdown("""
        # **Légende des niveaux de prix:**
        # - Économique: 0
        # - Modéré: 1
        # - Cher: 2
        # - Très cher: 3
        # - Luxe: 4
        # """)

        for summary in day_summaries:
            with st.expander(f"📅 Jour {summary['day']}"):
                if summary['hotel']:
                    hotel = summary['hotel']
                    rating_stars = "⭐" * int(hotel.get('rating', 0))
                    st.markdown(f"""
                    ### 🏨 Hôtel: {hotel.get('name','-')}
                    - Note: {hotel.get('rating','N/A')}/5{rating_stars}
                    - Niveau de prix: {get_price_level_description(hotel.get('price_level', 0))}
                    - Téléphone: {hotel.get('formatted_phone_number', 'N/A')}
                    - Ouvert maintenant: {'Oui' if hotel.get('is_open_now') else 'Non'}
                    - Adresse: {hotel.get('address','-')}
                    - {"[Site web](" + hotel['website'] + ")" if hotel.get('website') else "Site web: N/A"}
                    """)
                    if hotel.get('photo_url'):
                        st.image(hotel['photo_url'], width=100)
                st.markdown("### 🎯 Activités:")
                for activity in summary['activities']:
                    rating_stars = "⭐" * int(activity.get('rating', 0))
                    st.markdown(f"""
                    - **{activity.get('name','-')}** ({activity.get('type','-')})
                      - Note: {activity.get('rating','-')}/5{rating_stars}
                      - Adresse: {activity.get('address','-')}
                      - Horaire: {activity.get('time_slot', 'Toute la journée')}
                      - Niveau de prix: {get_price_level_description(activity.get('price_level', 0))}
                      - {"[Site web](" + activity['website'] + ")" if activity.get('website') else "Site web: N/A"}
                    """)
                    if activity.get('photo_url'):
                        st.image(activity['photo_url'], width=100)
        st.download_button(
            label="Télécharger l'itinéraire (PDF)",
            data=generate_pdf(st.session_state['recommendations']),
            file_name=f"itinerary_{city}.pdf",
            mime="application/pdf"
        )

if 'recommendations' in st.session_state:
    st.header("📋 Voulez-vous nous aider à améliorer ?")
    st.markdown("""
    Nous apprécions vos retours pour améliorer notre application.
    Veuillez remplir ce [formulaire Google Form](https://forms.gle/R7Z2QrwRig9uuSrk8) pour nous faire part de vos suggestions et de votre expérience.
    """)

###############""
# dérnier version qui fonctionne avec Hotel
import os
import streamlit as st
import requests
import folium
from geopy.distance import geodesic
from streamlit_folium import folium_static
import pandas as pd
from datetime import datetime, time
from utils.google_api import get_geocode_address, get_nearby_places, get_place_details, google_geolocate  # FIX: import google_geolocate
from utils.recommendations import generate_recommendations
from utils.weather import get_weather_forecast
from dotenv import load_dotenv
from fpdf import FPDF

# Charger les variables d'environnement
load_dotenv()
GOOGLE_PLACES_KEY = os.getenv("GOOGLE_PLACES_KEY")
VIATOR_API_KEY = os.getenv("VIATOR_API_KEY", "8cd8a095-d7c6-47ea-a0e7-9afacc40a0c5")
OPENWEATHERMAP_KEY = os.getenv("OPENWEATHERMAP_KEY")

import streamlit as st
import json
import os

# --- Fichier pour sauvegarder les préférences ---
PREF_FILE = "user_preferences.json"

def load_preferences():
    if os.path.exists(PREF_FILE):
        with open(PREF_FILE, "r") as f:
            return json.load(f)
    return {}

def save_preferences(prefs):
    with open(PREF_FILE, "w") as f:
        json.dump(prefs, f)

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

# ---------- Utilitaires locaux ----------
def _normalize_type_for_display(google_types):
    """
    Normalize Google place types to your app types.
    - 'lodging' -> 'hotel'  # FIX: clé pour afficher les hôtels
    - 'restaurant' -> 'restaurant'
    - 'tourist_attraction' -> 'tourist_attraction'
    """
    if not google_types:
        return None
    if 'lodging' in google_types:
        return 'hotel'
    if 'restaurant' in google_types:
        return 'restaurant'
    if 'tourist_attraction' in google_types:
        return 'tourist_attraction'
    # fallback: premier type Google
    return google_types[0]

def _build_photo_url(place):
    # FIX: utiliser photo depuis details OU depuis search quand details n’a rien
    photo_ref = None
    if place.get('photos'):
        photo_ref = place['photos'][0].get('photo_reference')
    if not photo_ref and place.get('details', {}).get('photos'):
        photo_ref = place['details']['photos'][0].get('photo_reference')
    if photo_ref and GOOGLE_PLACES_KEY:
        return f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={photo_ref}&key={GOOGLE_PLACES_KEY}"
    return None

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
    page = st.sidebar.radio("Navigation", ["🏠 Accueil", "⚙️ Confidentialité"])

    if page == "🏠 Accueil":
        # Titre et description
        st.title("🌍 Smart Travel Planner")
        st.markdown("""
        Planifiez votre voyage idéal avec des recommandations personnalisées basées sur les avis et les horaires d'ouverture.
        """)
        st.markdown("**💡 Conseils:**")
        st.markdown("- Utilisez les filtres pour affiner vos résultats et n’hésitez pas à élargir le rayon de recherche si nécessaire, afin d’obtenir plus de propositions d’activités.")
        st.markdown("- Les itinéraires sont optimisés en fonction de la météo et de vos préférences")
        # 👉 Ajouter ton code principal ici
    elif page == "⚙️ Confidentialité":
        privacy_settings_page()

    
    st.markdown("---")

    # Ajoutez ce CSS pour styliser le bouton
    st.markdown("""
    <style>
        .stButton > button {
            background-color: green;
            color: white;
        }
    </style>
    """, unsafe_allow_html=True)

    # ---------- Détection de position par défaut ----------
    if 'start_location' not in st.session_state:
        # FIX: stratégie en cascade: ipinfo -> Google Geolocation (si clé) -> message
        try:
            # 1) IP approx
            response = requests.get('https://ipinfo.io/json', timeout=5)
            data = response.json()
            if 'loc' in data:
                lat, lng = data['loc'].split(',')
                st.session_state['start_location'] = (float(lat), float(lng))
            # 2) Google Geolocation (plus précis si dispo)
            if os.getenv("GOOGLE_PLACES_KEY"):
                g_loc = google_geolocate()
                if g_loc:
                    st.session_state['start_location'] = (g_loc['lat'], g_loc['lng'])
            if 'start_location' in st.session_state:
                lat, lng = st.session_state['start_location']
                st.session_state['current_weather'] = get_weather_forecast(lat, lng)
                st.success(f"Position détectée automatiquement: {lat:.5f}, {lng:.5f}")
            else:
                st.error("Impossible de détecter votre position par défaut.")
        except Exception as e:
            st.error(f"Erreur de détection automatique: {e}")

    # Sidebar pour les filtres
    with st.sidebar:
        st.header("⚙️ Filtres")
        country = st.text_input("Pays", "France")
        city = st.text_input("Ville", "Paris")
        stay_duration = st.number_input("Durée du séjour (jours)", min_value=1, value=3)
        poi_types = st.multiselect(
            "Types de lieux",
            ["restaurant", "hotel", "tourist_attraction"],
            default=["restaurant", "hotel", "tourist_attraction"]
        )
        radius = st.slider("Rayon de recherche (mètres)", 100, 5000, 100)
        time_preferences = st.multiselect(
            "Préférences horaires",
            ["Matin (8h-12h)", "Midi (12h-14h)", "Soir (18h-22h)"],
            default=["Matin (8h-12h)", "Midi (12h-14h)", "Soir (18h-22h)"]
        )
        min_rating = st.slider("Note minimale", 1.0, 5.0, 4.0, 0.1)
        detect_location = st.button("📍 Détecter ma position")

    # Détection de la position à la demande
    if detect_location:
        try:
            # IP approx
            lat_lng = None
            response = requests.get('https://ipinfo.io/json', timeout=5)
            data = response.json()
            if 'loc' in data:
                lat, lng = data['loc'].split(',')
                lat_lng = (float(lat), float(lng))

            # Google Geolocation si possible
            g_loc = google_geolocate()
            if g_loc:
                lat_lng = (g_loc['lat'], g_loc['lng'])

            if lat_lng:
                st.session_state['start_location'] = lat_lng
                st.success(f"Position détectée: {lat_lng[0]:.5f}, {lat_lng[1]:.5f}")
                st.session_state['current_weather'] = get_weather_forecast(lat_lng[0], lat_lng[1])
            else:
                st.error("Impossible de détecter votre position.")
        except Exception as e:
            st.error(f"Erreur de détection: {e}")

    # Fonction pour générer un PDF
    def generate_pdf(recommendations):
        pdf = FPDF()
        try:
            pdf.add_font('DejaVu', '', 'DejaVuSansCondensed.ttf', uni=True)
            pdf.set_font('DejaVu', '', 12)
        except:
            pdf.set_font("Arial", size=12)
        pdf.add_page()
        for day, day_pois in recommendations.items():
            clean_day_text = day.encode('latin1', 'ignore').decode('latin1')
            pdf.cell(200, 10, txt=clean_day_text, ln=True, align='C')
            pdf.cell(200, 10, txt="Hôtel:", ln=True)
            hotels = [poi for poi in day_pois if poi.get('type') == 'hotel']
            for hotel in hotels:
                clean_text = f"Nom: {hotel['name']}, Note: {hotel.get('rating','N/A')}".encode('latin1', 'ignore').decode('latin1')
                pdf.cell(200, 10, txt=clean_text, ln=True)
            pdf.cell(200, 10, txt="Activités:", ln=True)
            for poi in day_pois:
                if poi.get('type') != 'hotel':
                    activity_text = f"Activité: {poi['name']} ({poi.get('type', '')})"
                    clean_activity_text = activity_text.encode('latin1', 'ignore').decode('latin1')
                    pdf.cell(200, 10, txt=clean_activity_text, ln=True)
                    if 'time_slot' in poi:
                        clean_time_slot = str(poi['time_slot']).encode('latin1', 'ignore').decode('latin1')
                        pdf.cell(200, 10, txt=f"Créneau: {clean_time_slot}", ln=True)
        byte_array_output = pdf.output(dest='S')
        if isinstance(byte_array_output, bytearray):
            byte_array_output = bytes(byte_array_output)
        return byte_array_output

    # Recherche
    if st.button("Rechercher"):
        with st.spinner("Recherche des meilleurs lieux..."):
            try:
                location = get_geocode_address(f"{city}, {country}")
                if not location:
                    st.error(f"Impossible de trouver {city}. Essayez une autre ville.")
                    st.stop()
                lat, lng = location['lat'], location['lng']
                st.session_state['start_location'] = (lat, lng)
                st.write(f"Coordonnées pour {city}: {lat}, {lng}")
                st.session_state['current_weather'] = get_weather_forecast(lat, lng)

                all_pois = []
                for poi_type in poi_types:
                    # FIX: conversion 'hotel' -> type Google 'lodging' pour obtenir des hôtels
                    g_type = 'lodging' if poi_type == 'hotel' else poi_type
                    pois = get_nearby_places((lat, lng), radius, g_type)
                    for poi in pois:
                        details = get_place_details(poi.get('place_id'))
                        # Construire un objet "place" enrichi pour extractions homogènes
                        place = {
                            'name': poi.get('name') or details.get('name'),
                            'place_id': poi.get('place_id'),
                            'google_types': details.get('types') or poi.get('types', []),
                            'address': details.get('vicinity') or details.get('formatted_address') or poi.get('vicinity'),
                            'latitude': details.get('geometry', {}).get('location', {}).get('lat') or poi.get('geometry', {}).get('location', {}).get('lat'),
                            'longitude': details.get('geometry', {}).get('location', {}).get('lng') or poi.get('geometry', {}).get('location', {}).get('lng'),
                            'rating': details.get('rating', poi.get('rating', 0)),
                            'reviews': details.get('reviews', []),
                            'website': details.get('website'),
                            'price_level': details.get('price_level', poi.get('price_level', 0)),
                            'formatted_phone_number': details.get('formatted_phone_number', details.get('international_phone_number')),
                            'opening_hours_raw': details.get('opening_hours', {}),
                            'details': details,
                            'photo_url': None
                        }
                        # Type normalisé
                        place['type'] = _normalize_type_for_display(place['google_types'])
                        # Photo
                        place['photo_url'] = _build_photo_url(place)
                        # Distance
                        if place['latitude'] is not None and place['longitude'] is not None:
                            place['distance'] = geodesic((lat, lng), (place['latitude'], place['longitude'])).meters
                        else:
                            place['distance'] = None
                        # Horaires
                        opening_hours = place['opening_hours_raw'] or {}
                        place['opening_hours'] = opening_hours.get('weekday_text', []) if isinstance(opening_hours, dict) else []
                        place['is_open_now'] = opening_hours.get('open_now') if isinstance(opening_hours, dict) else None

                        # On ne garde que les types qui nous intéressent réellement
                        if place['type'] in {"hotel", "restaurant", "tourist_attraction"}:
                            all_pois.append(place)

                if not all_pois:
                    st.error("Aucun lieu trouvé. Essayez d'élargir le rayon.")
                    st.stop()

                pois_df = pd.DataFrame(all_pois)
                st.session_state['pois'] = pois_df

                recommendations = generate_recommendations(
                    pois_df, min_rating=min_rating, stay_duration=stay_duration, time_preferences=time_preferences,
                    weather=st.session_state['current_weather']
                )
                st.session_state['recommendations'] = recommendations
            except Exception as e:
                st.error(f"Erreur lors de la recherche: {e}")

    # Affichage des résultats
    if 'recommendations' in st.session_state:
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.session_state.get('current_weather'):
                weather = st.session_state['current_weather']
                # FIX: conseil météo plus fiable (pluie/orage/bruine/neige/vent)
                advice = "Temps idéal pour les activités extérieures"
                desc = weather.get('description', '').lower()
                if any(k in desc for k in ["pluie", "orage", "bruine", "neige"]):
                    advice = "Prévoyez un parapluie et privilégiez les activités en intérieur"
                elif any(k in desc for k in ["vent", "rafale"]):
                    advice = "Évitez les hauteurs exposées et les activités nautiques"
                st.markdown(f"""
                ### 🌦️ Météo pour {city.upper()}
                - **Température**: {weather.get('temp','-')}°C
                - **Conditions**: {weather.get('description','-')}
                - **Conseil**: {advice}
                """)

            st.header("🏆 Itinéraire Optimisé")
            m = folium.Map(location=st.session_state['start_location'], zoom_start=14)
            folium.Marker(
                location=st.session_state['start_location'],
                popup='Votre position',
                icon=folium.Icon(color='red', icon='home')
            ).add_to(m)

            legend_html = """
            <div style="position: fixed; bottom: 50px; left: 50px; width: 180px; height: 140px; border:2px solid grey; z-index:9999; font-size:14px; background-color:white; padding:8px;">
            <b>Légende:</b><br>
            <i class="fa fa-map-marker" style="color:blue"></i> Jour 1<br>
            <i class="fa fa-map-marker" style="color:green"></i> Jour 2<br>
            <i class="fa fa-map-marker" style="color:purple"></i> Jour 3<br>
            <i class="fa fa-road" style="color:orange"></i> Trajet
            </div>
            """
            m.get_root().html.add_child(folium.Element(legend_html))

            day_summaries = []
            previous_location = st.session_state['start_location']
            colors = ['blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige']

            for day_num, (day, day_pois) in enumerate(st.session_state['recommendations'].items(), 1):
                color = colors[day_num % len(colors)]
                day_summary = {"day": day_num, "activities": [], "hotel": None}
                seen_places = set()

                for poi in day_pois:
                    if poi['place_id'] in seen_places:
                        continue
                    seen_places.add(poi['place_id'])

                    icon_type = {
                        'hotel': 'bed',
                        'restaurant': 'utensils',
                        'tourist_attraction': 'star'
                    }.get(poi.get('type'), 'info-sign')

                    folium.Marker(
                        location=[poi['latitude'], poi['longitude']],
                        popup=f"""
                        <div style="width: 220px;">
                            <b>{poi['name']}</b><br>
                            Type: {poi.get('type','-')}<br>
                            Note: {poi.get('rating','-')}⭐<br>
                            Adresse: {poi.get('address', 'Non renseignée')}<br>
                            {f"<img src='{poi['photo_url']}' width='100%'><br>" if poi.get('photo_url') else ""}
                            {f"<a href='{poi['website']}' target='_blank'>Site web</a><br>" if poi.get('website') else ''}
                        </div>
                        """,
                        icon=folium.Icon(color=color, icon=icon_type, prefix='fa')
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
                    else:
                        day_summary["activities"].append(poi)

                day_summaries.append(day_summary)

            folium_static(m, width=700, height=500)

        with col2:
            st.markdown("### Légende des Jours")
            for day_num in range(1, stay_duration + 1):
                color = colors[day_num % len(colors)]
                st.markdown(f"- Jour {day_num}: <span style='color:{color}'>■</span>", unsafe_allow_html=True)

        st.header("📝 Résumé de votre voyage")
        for summary in day_summaries:
            with st.expander(f"📅 Jour {summary['day']}"):
                if summary['hotel']:
                    hotel = summary['hotel']
                    st.markdown(f"""
                    ### 🏨 Hôtel: {hotel.get('name','-')}
                    - Note: {hotel.get('rating','N/A')}⭐
                    - Niveau de prix: {hotel.get('price_level', 'N/A')}
                    - Téléphone: {hotel.get('formatted_phone_number', 'N/A')}
                    - Ouvert maintenant: {'Oui' if hotel.get('is_open_now') else 'Non'}
                    - Adresse: {hotel.get('address','-')}
                    - {"[Site web](" + hotel['website'] + ")" if hotel.get('website') else "Site web: N/A"}
                    """)
                    if hotel.get('photo_url'):
                        st.image(hotel['photo_url'], width=100)

                st.markdown("### 🎯 Activités:")
                for activity in summary['activities']:
                    st.markdown(f"""
                    - **{activity.get('name','-')}** ({activity.get('type','-')})
                      - Note: {activity.get('rating','-')}⭐
                      - Adresse: {activity.get('address','-')}
                      - Horaire: {activity.get('time_slot', 'Toute la journée')}
                      - {"[Site web](" + activity['website'] + ")" if activity.get('website') else "Site web: N/A"}
                    """)
                    if activity.get('photo_url'):
                        st.image(activity['photo_url'], width=100)

        st.download_button(
            label="Télécharger l'itinéraire (PDF)",
            data=generate_pdf(st.session_state['recommendations']),
            file_name=f"itinerary_{city}.pdf",
            mime="application/pdf"
        )

if 'recommendations' in st.session_state:
    st.header("📋 Voulez-vous nous aider à améliorer ?")
    st.markdown("""
    Nous apprécions vos retours pour améliorer notre application.
    Veuillez remplir ce [formulaire Google Form](https://forms.gle/R7Z2QrwRig9uuSrk8) pour nous faire part de vos suggestions et de votre expérience.
    """)
