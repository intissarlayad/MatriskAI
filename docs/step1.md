# Étape 1 — Feature Engineering & Historique

Le script `matrisk_step1_cleaning.py` est le socle de MatriskAI. Il ingère les données brutes chaotiques et produit un dataset immaculé prêt pour l'apprentissage automatique, tout en gérant l'historisation temporelle indispensable à Prophet (Step 3).

## 1. Objectif Principal

* **Transformer le brut** : Convertir les 50 colonnes du fichier Excel source en 13 features ML exploitables.
* **Historiser** : Sauvegarder un "snapshot" daté à chaque exécution pour nourrir l'historique longitudinal des matériaux.

## 2. Processus Détaillé (Le Pipeline de Nettoyage)

Le nettoyage s'effectue selon les étapes séquentielles suivantes :

1. **Ingestion & Détection Automatique** : Lecture du fichier `QML report by Plant.xlsx`. La fonction intelligente `detect_column()` (issue de `config.py`) scanne les noms de colonnes et retrouve ses petits, même si l'ERP a légèrement modifié le nommage ("STMaterialCode" vs "MaterialCode").
2. **Encodage Discret** : Mapping des statuts QML et ASL textuels vers des scores de gravité numériques (0 à 4).
3. **Création du Score Combiné** : `combined_risk_score` = `(0.6 * qml_score) + (0.4 * asl_score)`. Le QML a un poids légèrement supérieur.
4. **Calcul Temporel** : Extraction de la date de mise à jour et calcul des `days_since_update` par rapport à la date du jour. Création du flag `date_inconnue` si la cellule est vide.
5. **NLP Basique** : Analyse des commentaires via recherche de mots-clés (regex) pour générer le `text_risk_flag`. Les mots comme "expired", "delay", "issue" déclenchent le drapeau.
   ```{image} _static/images/datasetnlp_excel.jpeg
   :alt: Extraction NLP depuis Excel
   :width: 100%
   :align: center
   ```
6. **Évaluation Logistique** : Calcul du risque lié à la durée de vie (`shelf_life_risk`) et détection des sécurités (certificats, backups de sous-usines).
7. **Synthèse Heuristique** : Calcul du `score_confiance` de la donnée et du `SRI` final selon la formule analytique.
8. **Labellisation** : Déduction du `risk_label` (Faible, Moyen, Élevé) basé sur les seuils du SRI définis dans la configuration.

## 3. Historique & Snapshots

L'IA prédictive temporelle a besoin de profondeur. À chaque exécution, Step 1 fait deux choses :

1. **Snapshot Mensuel** : Enregistre un CSV daté (ex: `snapshot_2026-05-24.csv`) dans le dossier `Snapshots/`.
2. **Historique Cumulé** : Met à jour (append) le fichier maître `historique_sri.csv`. C'est ce fichier qui contient l'évolution du SRI de chaque matériau mois après mois.

## 4. Les Corrections Critiques de la Version 4.2

La version v4.2 a introduit des correctifs MLOps majeurs pour rendre l'Étape 1 robuste aux environnements de production :

```{important} Correction de la Vitesse de Dégradation
Auparavant, de très vieilles dates de mise à jour provoquaient des valeurs aberrantes de `vitesse_degradation` (ex: -1000). La v4.2 introduit un **capping mathématique** : `.clip(lower=-5.0, upper=5.0)`. Cela stabilise l'entrée du réseau XGBoost.
```

```{important} Déduplication Stricte
Si le pipeline est relancé deux fois le même mois, les snapshots étaient dupliqués, ce qui détruisait l'analyse de séries temporelles de Prophet. La v4.2 implémente `drop_duplicates(subset=["Code", "Snapshot_Date"], keep="last")` sur l'historique global pour garantir l'intégrité temporelle.
```

## 5. Exécution & Outputs

**Commande de lancement :**
```bash
python matrisk_step1_cleaning.py
```

**Fichiers générés :**
* `Fichiers Excel/dataset_clean.csv` : Le dataset final de 1978 lignes.
  ```{image} _static/images/datasetcleanned_excel.jpeg
  :alt: Dataset Nettoyé
  :width: 100%
  :align: center
  ```
* `historique_sri.csv` : L'historique cumulé.
* `Snapshots/snapshot_YYYY-MM-DD.csv` : La sauvegarde de la session.
