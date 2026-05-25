# Dataset & Features

## 1. Description du Dataset

Le système MatriskAI ingère un rapport de qualité fournisseur brut : `QML report by Plant.xlsx`.

* **Taille** : Environ 1 978 lignes, représentant des matériaux industriels uniques.
* **Complexité** : 50 colonnes contenant des données hétérogènes (textes libres, dates de péremption, statuts d'approbation catégoriels, codes alphanumériques).
* **Défi** : Le rapport brut est conçu pour être lu par un humain, pas par un algorithme. Il contient des valeurs manquantes, des abréviations et des commentaires non structurés.

## 2. Les 13 Features Calculées

L'objectif de l'Étape 1 (Feature Engineering) est de distiller ces 50 colonnes en **13 caractéristiques (features)** hautement prédictives, quantitatives et normalisées, prêtes pour le Machine Learning.

| Feature | Description | Type | Exemple |
|:---|:---|:---|:---|
| `qml_risk_score` | Statut QML encodé selon sa sévérité (0=Certified → 4=Disqualified). | `int` | `3` |
| `asl_risk_score` | Statut ASL encodé de manière similaire. | `int` | `4` |
| `combined_risk_score` | Score composite pondéré : (0.6 × QML) + (0.4 × ASL). | `float` | `3.4` |
| `days_since_update` | Nombre de jours écoulés depuis la dernière mise à jour du dossier. | `int` | `794` |
| `date_inconnue` | Flag binaire (1=vrai) si la date de mise à jour est introuvable/manquante. | `binary` | `0` |
| `vitesse_degradation` | Évolution temporelle du risque (ΔSRI/temps), bornée entre -5.0 et +5.0. | `float` | `-1.2` |
| `shelf_life_risk` | Risque lié à la péremption (0: >12 mois, 1: 6-12 mois, 2: 3-6 mois, 3: <3 mois). | `int` | `1` |
| `has_ecertificate` | Présence vérifiée d'un e-Certificate de conformité (1=Oui). | `binary` | `1` |
| `has_subplant_backup` | Présence d'un site de production alternatif (1=Oui). | `binary` | `0` |
| `text_risk_flag` | Score NLP détectant des mots-clés de risque dans les commentaires libres. | `int` | `3` |
| `score_confiance` | Heuristique mesurant la qualité et la complétude des données (0-100). | `float` | `75.0` |
| `SRI` | *Supply Risk Index* global synthétique (0-100, 100 étant parfaitement sûr). | `float` | `47.7` |
| `risk_label` | Label de risque final déduit du SRI (Faible / Moyen / Élevé). | `str` | `Moyen` |

```{note}
Pour l'entraînement XGBoost (Step 2), les colonnes `SRI`, `risk_label` et `score_confiance` sont strictement exclues afin d'éviter tout phénomène de *Data Leakage*.
```

## 3. Distribution des Classes (Class Imbalance)

Le dataset reflète la réalité d'une Supply Chain opérationnelle : la grande majorité des matériaux sont conformes, et les anomalies critiques sont rares.

* **Faible (SRI >= 65)** : ~1 853 matériaux (93.7%)
* **Moyen (40 <= SRI < 65)** : ~81 matériaux (4.1%)
* **Élevé (SRI < 40)** : ~44 matériaux (2.2%)

**Impact sur l'Intelligence Artificielle :**
Ce déséquilibre majeur (imbalanced dataset) rend l'apprentissage difficile. Un modèle naïf prédirait "Faible" systématiquement et obtiendrait 93.7% de précision. Pour contrer cela, MatriskAI utilise l'optimisation des hyperparamètres de XGBoost (notamment la gestion des poids d'échantillons ou la profondeur des arbres) et adapte sa stratégie de calibration.

## 4. Encodages des Statuts (QML / ASL)

Les statuts textuels sont convertis en scores de risque (de 0 à 4, 4 étant le pire).

**QML_MAP (Qualified Manufacturer List) :**
* `C:Certified` → **0** (Risque nul)
* `Q:Qualified` → **1** (Risque faible)
* `I:Initiation` / `X:Created by DMS` → **2** (Risque modéré, en cours)
* `O:Obsolete` → **3** (Risque élevé, à remplacer)
* `D:Disqualified` → **4** (Risque critique, interdit)

**ASL_MAP (Approved Supplier List) :**
* `A:Approved` → **0** 
* `W:Waived` → **1**
* `I:Initiation` → **2**
* `P:Probation` → **3**
* `D:Disapproved` → **4**

## 5. Algorithme de Calcul du SRI

Le SRI n'est pas prédit (il est calculé analytiquement dans l'Étape 1), il sert de socle pour créer la variable cible (`risk_label`).

La formule du SRI part d'un score parfait de 100, auquel on soustrait des pénalités pondérées :
1. **Statut de Base** : Déduit fortement le SRI si le `combined_risk_score` est élevé.
2. **Obsolescence Documentaire** : Pénalise si `days_since_update` est très élevé.
3. **Péremption** : Pénalise selon le `shelf_life_risk`.
4. **Signaux Faibles** : Pénalise si le NLP détecte un `text_risk_flag`.
5. **Bonus** : Rajoute de légers points si des sécurités existent (`has_ecertificate`, `has_subplant_backup`).

**Seuils de classification :**
* Si SRI >= 65 → **Faible**
* Si SRI >= 40 → **Moyen**
* Si SRI < 40 → **Élevé** (Action critique requise)
