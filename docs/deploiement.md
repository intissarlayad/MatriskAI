# Déploiement Cloud & Mode SaaS

MatriskAI est disponible en production sous forme d'application Cloud **SaaS (Software as a Service)**. Cela permet à n'importe quelle entreprise ou direction Supply Chain d'utiliser le système d'intelligence artificielle immédiatement, de manière sécurisée et sans aucune installation technique.

## 🔗 Accès à la Plateforme

L'application de production est hébergée sur le cloud Streamlit Sharing :

🌐 **Lien d'accès public :** [matriskai.streamlit.app](https://matriskai.streamlit.app)

---

## 🔒 Confidentialité & Sécurité des Données

La sécurité des données industrielles est une priorité absolue. C'est pourquoi l'application de production respecte les principes suivants :
* **Zéro Stockage Persistant** : Vos fichiers Excel importés et les résultats calculés sont traités uniquement en mémoire vive (RAM) durant votre session. Rien n'est écrit ou conservé sur le serveur Cloud une fois l'onglet fermé.
* **Environnement Étanche** : Chaque session utilisateur est totalement isolée des autres.
* **Exclusion Git** : Les fichiers contenant des données réelles ou des clés API sont exclus du dépôt public grâce à notre fichier `.gitignore`.

---

## 🛠️ Démarche de Travail (Workflow SaaS)

Lorsqu'une entreprise accède au site pour la première fois, l'écran affiche **« Données non disponibles »**. C'est le comportement attendu puisque l'environnement est initialement vierge de toute donnée pour garantir la confidentialité.

Voici les étapes simples pour auditer vos données :

### 1. Préparation du Fichier
Assurez-vous de disposer de votre fichier Excel de données fournisseurs (par exemple le rapport QML brut au format `.xlsx` ou `.xls`). Les colonnes seront automatiquement mappées grâce à notre système de détection intelligente (`config.py`).

### 2. Importation des Données (Upload)
1. Rendez-vous sur l'onglet **Données & Pipeline** dans la barre latérale gauche.
2. Cliquez sur la zone d'importation de fichier ou glissez-déposez votre fichier Excel.
3. Le tableau affiche un aperçu de vos données brutes pour confirmer la bonne lecture.

### 3. Exécution du Pipeline IA
1. Toujours dans l'onglet **Données & Pipeline**, cliquez sur le bouton **« Déployer ! »** (ou « Run Pipeline »).
2. Le système va exécuter en tâche de fond le pipeline complet de Data Science (en quelques secondes) :
   * **Étape 1** : Nettoyage et calcul des 13 features (SRI, vitesse de dégradation, etc.).
   * **Étape 2** : Inférence par le modèle XGBoost et détection d'anomalies (IsolationForest).
   * **Étape 3** : Prévisions temporelles (Prophet & Régression Linéaire) à J+30 et J+90.
   * **Étape 4** : Génération du plan d'actions prescriptif (les 15 règles métiers).

### 4. Analyse des Résultats & Décision
Une fois l'exécution terminée, tous les onglets du tableau de bord se mettent à jour automatiquement :
* **Vue Globale** : Affiche les indicateurs clés (KPIs) et le résumé exécutif.
* **Heatmap & Alertes** : Identifie instantanément les fournisseurs à risque critique (alertes 🔴 URGENT et 🟡 ATTENTION).
* **Time Series IA** : Permet de filtrer par fournisseur et de voir les courbes de prévision à 3 mois.
* **Assistant IA (Groq)** : Permet de poser des questions en langage naturel pour explorer les résultats complexes ou demander des explications sur les recommandations.
