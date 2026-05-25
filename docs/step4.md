# Étape 4 — Moteur Prescriptif

Le script `matrisk_step4_prescriptif.py` est l'aboutissement métier du projet MatriskAI. Prédire qu'un composant va manquer (Étape 2 et 3) est insuffisant. Il faut dire aux équipes de la Supply Chain *exactement* ce qu'elles doivent faire aujourd'hui pour l'éviter. C'est le rôle de l'Étape 4.

## 1. Objectif Principal

* **Traduire la donnée en action** : Appliquer un set de règles métiers strictes sur les prédictions (XGBoost), les anomalies (IsolationForest) et les prévisions (Prophet).
* **Générer un Plan d'Actions** : Un fichier CSV contenant la liste des tâches (ToDo) à affecter aux responsables qualité.
* **Résumer la situation** : Créer un texte exécutif (NLP) lisible par un humain.

## 2. Les 15 Règles Prescriptives (Système Expert)

MatriskAI intègre un système expert basé sur des conditions logiques. Voici un extrait des règles principales appliquées à chaque ligne de matériau :

| ID Règle | Déclencheur (Condition) | Action Prescrite | Catégorie |
|:---|:---|:---|:---|
| **R01** | `risk_label == 'Élevé'` | Lancer une procédure URGENTE de requalification du fournisseur. Bloquer les commandes. | Requalification |
| **R02** | `is_anomaly == True` (IsolationForest) | Déclencher un audit de conformité fournisseur : profil atypique détecté. | Audit |
| **R03** | `forecast_SRI_90d < 40` (Prophet) | Dégradation anticipée : initier une réunion préventive avec le fournisseur. | Prévention |
| **R04** | `shelf_life_risk >= 2` (< 6 mois) | Alerte de péremption imminente : purger les stocks anciens et commander du frais. | Stock |
| **R05** | `has_subplant_backup == 0` et `risk == Moyen` | Monosourcing risqué : sourcer d'urgence un backup / fournisseur alternatif (Dual Sourcing). | Alternative |
| **R06** | `qml_score == 3` (Obsolète) | Le composant est obsolète. Initier le processus "Phase-out" / ingénierie de remplacement. | Requalification |
| **R07** | `days_since_update > 365` | Le dossier qualité a plus d'un an. Exiger une mise à jour documentaire (e-Certificate). | Audit |
| **R08** | `text_risk_flag == 1` (NLP) | Le commentaire contient des alertes sémantiques. Revue manuelle requise par un ingénieur. | Audit |

*(Note : le système interne possède 15 combinaisons logiques de ce type pour couvrir 360° du risque).*

## 3. Résultats & Métriques

Sur le dataset d'exemple de 1978 lignes, le moteur génère typiquement :

* **653 actions recommandées** au total.
* Celles-ci concernent environ **150 matériaux problématiques** (le reste ne déclenche aucune règle, selon le principe de gestion par exception).
* La majorité des actions se concentrent sur la mise à jour documentaire (`days_since_update`) et le traitement des obsolescences (`qml_score`).

## 4. Résumé Exécutif

L'algorithme génère automatiquement un fichier texte `step4_resume_executif.txt` contenant un condensé de la situation.

**Extrait généré :**
> "Le pipeline MatriskAI a scanné 1978 matériaux.
> 44 matériaux sont classés en risque ÉLEVÉ nécessitant une attention immédiate.
> 99 anomalies structurelles ont été détectées.
> Le moteur prescriptif a généré 653 tâches d'actions correctives."

Ce fichier est lu et affiché en première page du Dashboard Streamlit.

## 5. Exécution & Outputs

**Commande de lancement :**
```bash
python matrisk_step4_prescriptif.py
```

**Fichiers générés :**
* `step4_plan_actions.csv` : Le grand livre des actions (Code Matériel, Fournisseur, Action à réaliser, Urgence).
* `step4_resume_executif.txt` : Le texte de synthèse.
