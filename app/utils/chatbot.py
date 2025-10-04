import requests
import json
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

def query_mistral_api(prompt, model="mistral-tiny", temperature=0.7, max_tokens=300):
    """
    Interroge l'API de Mistral pour obtenir une réponse à une question.
    Args:
        prompt (str): La question ou le texte à envoyer à l'API.
        model (str): Le modèle à utiliser (par défaut "mistral-tiny").
        temperature (float): Paramètre pour contrôler la créativité de la réponse.
        max_tokens (int): Nombre maximum de tokens dans la réponse.
    Returns:
        str: La réponse de l'API.
    """
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"Erreur lors de l'appel à l'API Mistral: {response.text}")

def generate_recommendations_with_chatbot(user_prompt):
    """
    Génère des recommandations personnalisées et propose des événements basés sur le prompt de l'utilisateur.
    Args:
        user_prompt (str): Le prompt de l'utilisateur contenant ses préférences et détails du voyage.
    Returns:
        dict: Les recommandations et les événements générés par le chatbot.
    """
    # Prompt pour recommandations touristiques avec emojis
    prompt_reco = (
        f"🌟 Voici les préférences de l'utilisateur : {user_prompt}. "
        "Propose un programme de voyage personnalisé avec des activités, des restaurants et des hôtels adaptés. "
        "Inclue des emojis pour rendre les recommandations plus attrayantes. "
        "Propose également un hôtel pour chaque jour du séjour."
    )
    recommendations = query_mistral_api(prompt_reco)

    # Prompt pour événements gratuits ou existants avec emojis
    prompt_events = (
        f"🎉 Voici les préférences de l'utilisateur : {user_prompt}. "
        "Liste les événements gratuits à venir pour un visiteur. "
        "Si aucun événement gratuit n'est disponible, propose les événements les plus intéressants qui existent. "
        "Utilise des emojis pour rendre les suggestions plus attrayantes."
    )
    events = query_mistral_api(prompt_events, max_tokens=400)
    return {
        "recommendations": recommendations,
        "events": events
    }
