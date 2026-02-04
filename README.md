# Smart Travel Planner - Projet RNCP 37422

**Auteur** : Khadim Fall
**Date de soutenance** : 11/02/2026
**Technologies** : Python, Streamlit, GCP (Cloud Run, Secret Manager), GitHub Actions, Airflow, MLflow

## 📌 Objectifs du Projet
- **Planification de voyages intelligente** : Recommandations personnalisées (météo, budget, accessibilité).
- **Automatisation complète** : CI/CD avec GitHub Actions, déploiement sur GCP.
- **Sécurité et conformité RGPD** : Gestion des clés API via GitHub Secrets et Google Secret Manager.

## 🛠️ Installation
### Prérequis
- Compte GCP avec les APIs activées (Cloud Run, Secret Manager).
- Clés API pour :
  - Google Places
  - OpenWeatherMap
  - Mistral AI
  - DATAtourisme

### Déploiement
1. **Cloner le dépôt** :
   ```bash
   git clone https://github.com/votre-utilisateur/project_geo_tourisme.git
   cd project_geo_tourisme
