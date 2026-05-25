# Architecture du Système

## 1. Schéma du Pipeline

L'architecture de MatriskAI est modulaire et séquentielle. Chaque étape du pipeline a une responsabilité claire et bien définie.

```{image} _static/images/pipeline.png
:alt: Architecture du Pipeline MatriskAI
:width: 100%
:align: center
```

## 2. Vue d'ensemble de l'architecture

Le système est orchestré autour d'un pipeline en **4 étapes** principales, surmonté d'une interface utilisateur :

1. **Step 1 (Cleaning + Features)** : Ingestion des données brutes, nettoyage, et ingénierie des caractéristiques (Feature Engineering).
2. **Step 2 (XGBoost + Anomalies)** : Entraînement du modèle de classification (XGBoost), détection des anomalies non supervisée (IsolationForest), et analyse de l'explicabilité (SHAP).
3. **Step 3 (Prophet Forecast)** : Modélisation des séries temporelles pour prédire l'évolution des risques à court et moyen terme (J+90).
4. **Step 4 (Prescriptive Rules)** : Traduction des prédictions et des signaux de risque en un plan d'actions concrètes via un moteur de règles métiers.
5. **Dashboard Streamlit** : Interface visuelle interactive permettant aux utilisateurs d'explorer les résultats, de relancer le pipeline et d'interagir avec l'Assistant IA.

La configuration globale (chemins, paramètres, seuils) est centralisée dans le fichier `config.py`, ce qui rend le système extrêmement maintenable. Le script `run_pipeline.py` sert d'orchestrateur pour exécuter le flux de bout en bout de manière séquentielle.

## 3. Structure des Fichiers

Voici l'arborescence complète du projet MatriskAI :

```text
MatriskAI/
├── config.py                    # Configuration centrale (chemins, features, seuils)
├── run_pipeline.py              # Orchestrateur principal (lance toutes les étapes)
├── matrisk_step1_cleaning.py    # Feature Engineering & Gestion de l'historique
├── matrisk_step2_train.py       # Classification XGBoost & Détection d'anomalies
├── matrisk_step3_forecast.py    # Séries temporelles Prophet & Fallback linéaire
├── matrisk_step4_prescriptif.py # Moteur Prescriptif (règles métiers)
├── Scripts/
│   └── matrisk_step5_dashboard.py  # Application Dashboard Streamlit
├── Fichiers Excel/              # Dossier de données brutes et outputs nettoyés
│   ├── QML report by Plant.xlsx    # Fichier source principal
│   ├── dataset_clean.csv           # Output du Step 1
│   └── step2_predictions.csv       # Output du Step 2
├── Snapshots/                   # Sauvegardes mensuelles de l'état du dataset
├── Logs/                        # Journaux d'exécution détaillés par script
├── docs/                        # Documentation Sphinx (fichiers Markdown MyST)
├── requirements.txt             # Dépendances Python
├── Dockerfile                   # Fichier de conteneurisation
├── .env                         # Variables d'environnement (ex: GROQ_API_KEY)
└── README.md                    # Documentation de base du dépôt
```

## 4. Flux de Données

Le cycle de vie de la donnée au sein de MatriskAI suit un chemin strict :

1. **Entrée (Input)** : Le système lit le fichier brut `Fichiers Excel/QML report by Plant.xlsx` (ex: 1978 lignes, 50 colonnes).
2. **Output Step 1** : 
   - Génération de `dataset_clean.csv` (données prêtes pour le ML).
   - Mise à jour de `historique_sri.csv` (suivi longitudinal).
   - Création d'un instantané dans `Snapshots/`.
3. **Output Step 2** : 
   - Génération de `step2_predictions.csv` (contient les prédictions et probabilités XGBoost).
   - Sauvegarde du modèle entraîné `xgb_model.pkl`.
   - Génération des visuels SHAP.
4. **Output Step 3** : 
   - Export de `step3_forecast_fournisseurs.csv` (tendances par fournisseur).
   - Export de `step3_forecast_materiaux.csv` (tendances par matériau).
5. **Output Step 4** : 
   - Création du `step4_plan_actions.csv` (tableau des recommandations).
   - Génération du `step4_resume_executif.txt` (synthèse textuelle).
6. **Consommation** : Le Dashboard (Step 5) lit l'ensemble de ces fichiers `.csv` générés dans le dossier `Fichiers Excel/` et le dossier racine pour alimenter l'interface visuelle.

## 5. Dépendances Techniques

MatriskAI s'appuie sur une stack robuste et open-source dédiée à la Data Science :

| Bibliothèque | Rôle dans MatriskAI |
|:---|:---|
| **pandas** & **numpy** | Manipulation des DataFrames, algèbre linéaire, nettoyage de données. |
| **scikit-learn** | Calibration isotonique, IsolationForest, métriques d'évaluation, preprocessing. |
| **xgboost** | Algorithme de Gradient Boosting utilisé pour la classification principale (Faible/Moyen/Élevé). |
| **prophet** | Modélisation bayésienne des séries temporelles pour les prévisions à J+90. |
| **shap** | Interprétabilité et explicabilité locale et globale du modèle XGBoost. |
| **streamlit** | Framework de création de l'interface utilisateur web interactive. |
| **plotly** & **matplotlib** | Visualisations interactives et génération de graphiques statiques. |
| **groq** | Client API pour connecter l'Assistant IA (LLM très haute vitesse). |
