# Étape 2 — XGBoost, Calibration & Anomalies

Le script `matrisk_step2_train.py` est le cœur analytique (Machine Learning) du pipeline. Il apprend des historiques pour classer instantanément les risques, repérer les anomalies et expliquer ses décisions de manière transparente.

## 1. Objectifs

1. **Classification Supervisée** : Entraîner un modèle XGBoost pour classifier les matériaux en Faible, Moyen ou Élevé selon les 10 features ML.
2. **Détection d'Anomalies (Non Supervisée)** : Identifier les "moutons noirs" du dataset avec IsolationForest.
3. **Explicabilité (XAI)** : Utiliser SHAP pour comprendre pourquoi le modèle considère tel matériau comme "Élevé".

## 2. Le Moteur XGBoost

XGBoost (eXtreme Gradient Boosting) est l'algorithme choisi pour sa robustesse face aux données tabulaires et sa résistance naturelle au surapprentissage.

* **Features utilisées** : Uniquement les 10 variables listées dans `ML_FEATURES` (config.py). 
* **Anti-Data Leakage** : `SRI`, `risk_label` et `score_confiance` sont strictement retirés avant l'entraînement.
* **Validation Croisée** : Utilisation d'un K-Fold (5 splits) pour s'assurer que le modèle généralise bien.
* **Performances Typiques** : 
  * Accuracy sur le Test Set : **88.8%**
  * F1-Score (Cross-Validation) : **0.996 ± 0.003**

## 3. Calibration Isotonique (Correctif v4.2)

Par défaut, XGBoost est mauvais pour estimer des *probabilités* réelles (il donne des scores relatifs). On utilise donc un `CalibratedClassifierCV` (méthode isotonique) pour transformer les sorties brutes en probabilités fiables.

```{warning} Le Problème de la v4.1
Dans les versions précédentes, la rareté extrême de la classe "Élevé" (parfois < 5 instances dans un split de test) faisait crasher la calibration isotonique.
```
**Solution v4.2 (Fallback Dynamique)** : Le système inspecte le nombre d'échantillons de la classe minoritaire. S'il y a moins de 3 échantillons (`min_class_count < 3`), MatriskAI contourne automatiquement la calibration et utilise les probabilités brutes de XGBoost. Le pipeline devient ainsi 100% *fault-tolerant*.

## 4. Détection d'Anomalies (IsolationForest)

En parallèle, le script lance un `IsolationForest`. 
* **Objectif** : Trouver des points de données qui "ne ressemblent pas aux autres", indépendamment du label de risque. (Ex: Un composant certifié mais avec une vitesse de dégradation incohérente).
* **Contamination** : Fixée à 0.05. Le modèle est configuré pour identifier les **5%** les plus anormaux.
* **Résultat typique** : Environ 99 anomalies détectées sur 1978 lignes.

## 5. Explicabilité avec SHAP

Pour qu'un modèle soit accepté par les experts Supply Chain, il ne doit pas être une boîte noire. SHAP (SHapley Additive exPlanations) décortique l'impact de chaque feature.

### Impact Global (Bar Plot)
Quelles sont les features qui comptent le plus en général ?
```{image} _static/images/shap_importance_bar.png
:alt: SHAP Feature Importance
:width: 80%
:align: center
```
*Le statut QML et ASL dominent généralement l'importance.*

### Impact Local (Beeswarm - Classe Élevé)
Pourquoi le modèle déclenche-t-il l'alerte "Élevé" spécifiquement ?
```{image} _static/images/shap_beeswarm_eleve.png
:alt: SHAP Beeswarm Plot - Classe Élevé
:width: 80%
:align: center
```
*Un point rouge vers la droite signifie qu'une valeur haute de la feature augmente drastiquement la probabilité d'être classé 'Élevé'.*

## 6. Exécution & Outputs

**Commande de lancement :**
```bash
python matrisk_step2_train.py
```

**Fichiers générés :**
* `Fichiers Excel/step2_predictions.csv` : Le dataset enrichi des prédictions, probabilités (Faible/Moyen/Elevé), anomalies et top-recommandations issues de SHAP.
* `xgb_model.pkl` : Le modèle sérialisé pour le Dashboard.
* `shap_importance_bar.png` et `shap_beeswarm_eleve.png`.
* `step2_rapport_performance.txt` : Rapport textuel des métriques.
