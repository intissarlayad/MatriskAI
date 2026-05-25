# Dashboard Streamlit

Le fichier `Scripts/matrisk_step5_dashboard.py` sert d'interface graphique (GUI) globale pour le projet MatriskAI. Il permet aux décideurs non-techniques de consommer les résultats complexes (ML, XAI, séries temporelles) de manière visuelle, intuitive et interactive.

## 1. Vue d'ensemble

Le dashboard est entièrement codé en Python à l'aide du framework open-source **Streamlit**. Il ne nécessite aucune connaissance en HTML/JS.

* **Données Consommées** : Il charge dynamiquement les fichiers `.csv` générés par les étapes 1 à 4 (situés dans `Fichiers Excel/` et à la racine).
* **Mode Thématique** : Il supporte nativement le mode Clair (Light) et Sombre (Dark), configurable en haut à droite de l'application.

## 2. Aperçu de l'Interface

```{image} _static/images/dashboard.png
:alt: Dashboard MatriskAI
:width: 100%
:align: center
```

## 3. Les Onglets Principaux

La navigation s'effectue via une barre latérale.

### A. Vue Globale (Overview)
L'écran de démarrage. Il affiche les métriques de haut niveau (KPIs) :
* Nombre total de matériaux scannés.
* Nombre de matériaux en risque Élevé (avec une coloration conditionnelle rouge).
* Le SRI moyen du parc (généralement autour de 47.7).
* Le nombre d'actions correctives en attente.
Il affiche également le résumé exécutif textuel généré à l'Étape 4.

### B. Données & Pipeline (Data & Execution)
Le panneau de contrôle technique :
* Permet d'uploader un nouveau fichier brut `.xlsx`.
* Affiche les tableaux de données brutes et nettoyées avec pagination.
* **Bouton d'exécution** : Un bouton permet de déclencher l'orchestrateur `run_pipeline.py` directement depuis l'interface web pour mettre à jour les prédictions.

### C. Time Series IA (Prophet)
Le centre de prévision :
* Affiche les graphiques générés par Prophet.
* Permet de sélectionner un fournisseur spécifique dans un menu déroulant pour visualiser la tendance passée de son SRI et le cône d'incertitude (intervalle de confiance) pour les 90 prochains jours.

### D. Prévisions J+90 (Forecast Alerts)
Le tableau de bord des alertes anticipées :
* Liste les 7 fournisseurs (ou plus) en statut 🔴 URGENT.
* Fournit un tableau triable des prévisions pour orienter les efforts d'audit des mois à venir.

## 4. Assistant IA (Groq)

L'une des innovations majeures de la v4 est l'intégration d'un Assistant IA conversationnel de nouvelle génération.

* **Technologie** : Il s'appuie sur un LLM (Large Language Model) via l'API **Groq**, réputée pour sa vitesse d'inférence foudroyante (LPU).
* **Fonctionnement** : Un onglet "Chat" permet à l'utilisateur de poser des questions en langage naturel.
* **Contexte métier** : Le chatbot est initialisé avec un prompt système (System Prompt) lui expliquant ce qu'est MatriskAI, le QML, l'ASL et le SRI. Il est capable d'expliquer les concepts du pipeline à l'utilisateur.

```{warning} Configuration Requise
Pour que le chatbot fonctionne, vous devez posséder une clé API Groq gratuite et la configurer dans un fichier `.env` à la racine du projet (`GROQ_API_KEY=gsk_...`).
```

## 5. Lancement de l'Application

Depuis la racine du projet, exécutez la commande suivante dans votre terminal :

```bash
streamlit run Scripts/matrisk_step5_dashboard.py
```

L'application s'ouvrira automatiquement dans votre navigateur par défaut à l'adresse `http://localhost:8501`.
