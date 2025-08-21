# Projet Airflow : Pipeline de Données Météo

## Description

Ce projet consiste à créer un DAG Airflow pour récupérer des données météo depuis l'API OpenWeatherMap, les transformer, et entraîner un modèle de prédiction. Le DAG est conçu pour s'exécuter toutes les minutes afin de mettre à jour régulièrement un dashboard et un modèle de prédiction.

## Structure du Projet

- `dags/weather_dag.py` : Contient la définition du DAG.
- `clean_data/` : Dossier pour stocker les données transformées.
- `raw_files/` : Dossier pour stocker les données brutes.

## Prérequis

- Docker
- Airflow
- Compte OpenWeatherMap avec une clé API

## Configuration

1. **Docker et Airflow** : Suivez les instructions pour configurer Docker et Airflow.
2. **Variable Airflow** : Créez une variable Airflow nommée `cities` avec la valeur `["paris", "clermont-ferrand", "london", "washington"]`.

## Exécution

1. Placez le fichier `weather_dag.py` dans le dossier `dags`.
2. Assurez-vous que les dossiers `clean_data` et `raw_files` sont créés et accessibles.
3. Déclenchez le DAG depuis l'interface utilisateur d'Airflow.

## Bonnes Pratiques

- **Gestion des Erreurs** : La gestion des erreurs pour la désérialisation de la variable `cities` a été ajoutée pour s'assurer que le code ne plante pas en cas de problème avec les variables Airflow. Si la variable n'est pas correctement désérialisée, une liste de villes par défaut est utilisée.

- **Décorateurs** : Utilisation des décorateurs `@dag`, `@task`, et `@task_group` pour définir le DAG, les tâches, et les groupes de tâches. Cela rend le code plus lisible et plus facile à maintenir.

- **Retries** : La tâche `fetch_weather_task` est configurée pour être réessayée 10 fois avec un délai de 10 secondes entre chaque tentative, même si elle réussit. Cela garantit que la tâche est exécutée plusieurs fois lors de la première exécution du DAG pour vérifier sa robustesse.

- **Utilisation de `.copy()`** : Cela montre une compréhension des bonnes pratiques avec Pandas, en évitant les problèmes potentiels liés aux vues de DataFrame.

- **Commentaires Markdown** : Des commentaires en Markdown ont été ajoutés pour expliquer chaque fonction et chaque partie du code, ce qui est essentiel pour la maintenance et la compréhension du code.

- **Taille des Tâches** : Les tâches sont conçues pour être petites et indépendantes.

- **Documentation** : Le code est bien documenté pour faciliter la compréhension et la maintenance.

- **Variables Airflow** : Utilisation de variables pour stocker les configurations et les rendre facilement modifiables.

## Auteurs

- Khadim Fall
