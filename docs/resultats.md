# Résultats & Perspectives

Cette page synthétise les performances techniques du pipeline MatriskAI (v4.2), les correctifs majeurs déployés, ainsi que la feuille de route (Roadmap) pour les futures itérations du projet.

## 1. Métriques de Performance (MLOps)

Le tableau suivant résume les performances du système sur le jeu de données actuel (1 978 matériaux).

| Composant | Métrique | Score / Résultat Typique |
|:---|:---|:---|
| **XGBoost (Classification)** | Précision (Accuracy) sur Test Set | **88.8 %** |
| **XGBoost (Classification)** | F1-Score Macro (Validation Croisée 5-folds) | **0.996 ± 0.003** |
| **XGBoost (Explicabilité)** | Confiance IA Moyenne | **85.1 – 86.3 / 100** |
| **Prophet (Prévisions)** | Alertes Fournisseurs projetées à J+90 | 🔴 7 URGENT, 🟡 13 ATTENTION, 🟢 56 OK |
| **IsolationForest (Anomalies)** | Taux de contamination fixé | **5.0 %** (soit 99 anomalies détectées) |
| **Moteur Prescriptif** | Actions générées vs Matériaux impactés | **653 actions** prescrites sur **150 matériaux** |

## 2. Visualisation des Résultats

Les capacités d'explicabilité de MatriskAI s'illustrent graphiquement.

**Distribution des Scores de Risque (SRI)** : Le système permet de voir rapidement si le parc fournisseur global se porte bien.
```{image} _static/images/sri_score.png
:alt: Distribution SRI
:width: 80%
:align: center
```

**Analyse SHAP des cas critiques** : L'IA explique ses choix via la théorie des jeux (Valeurs de Shapley).
```{image} _static/images/shap_beeswarm_eleve.png
:alt: SHAP Analysis
:width: 80%
:align: center
```

## 3. Historique des Corrections Critiques (v4.2)

La version 4.2 a permis de passer d'un "Proof of Concept" (PoC) académique à un système robuste de niveau ingénierie :

* **[CORRIGÉ] Dérive de la Vitesse de Dégradation** : Les matériaux non mis à jour depuis 10 ans provoquaient des scores aberrants (ex: `vitesse = -1500`). *Solution : Capping strict implémenté entre -5.0 et +5.0.*
* **[CORRIGÉ] Crash de la Calibration Isotonique** : Le pipeline plantait si un échantillon de validation ne contenait que 1 ou 2 exemples de la classe "Élevé". *Solution : Bypass dynamique de la calibration (fallback vers les probabilités brutes XGBoost) si `min_class_count < 3`.*
* **[CORRIGÉ] Duplication des Snapshots (Séries Temporelles)** : Exécuter le pipeline deux fois le même jour faussait Prophet. *Solution : Déduplication stricte par "Code + Snapshot_Date" sur le fichier d'historique central.*
* **[CORRIGÉ] Erreur Stan Prophet (Variance Nulle)** : Si l'historique d'un fournisseur était plat (aucune évolution du SRI), Prophet échouait à initialiser son moteur bayésien. *Solution : Bypass automatique vers une régression linéaire simple si la variance du SRI est nulle.*

## 4. Roadmap & Améliorations Futures

Voici la feuille de route technique pour la v5.0 :

* [x] **v4.2** : Normalisation de la vitesse de dégradation.
* [x] **v4.2** : Stratégie de calibration "Fault-Tolerant".
* [x] **v4.2** : Refonte complète de la documentation Sphinx/ReadTheDocs.
* [ ] **v5.0** : Intégration de **SMOTE** ou gestion fine des `class_weights` pour mieux gérer l'extrême rareté de la classe "Élevé" (Class Imbalance).
* [ ] **v5.0** : Automatisation **CI/CD** (GitHub Actions / GitLab CI) pour déclencher l'entraînement du modèle chaque 1er du mois de manière asynchrone.
* [ ] **v5.1** : Module d'export direct vers les ERP du marché (SAP, Oracle) via API REST.
* [ ] **v5.2** : Migration optionnelle du Dashboard Streamlit vers **Power BI** pour une meilleure intégration au sein des systèmes informatiques corporate.

## 5. Perspectives Académiques

Ce projet démontre la pertinence d'appliquer des techniques avancées d'Intelligence Artificielle (XAI, Bayésien) à la Supply Chain. Les futurs travaux de recherche pourraient se pencher sur l'utilisation de l'**AutoML** pour optimiser dynamiquement le choix du modèle de classification en fonction des dérives de données (Data Drift) observées au fil des mois, ainsi que l'intégration du framework **MLflow** pour le suivi expérimental des hyperparamètres XGBoost.
