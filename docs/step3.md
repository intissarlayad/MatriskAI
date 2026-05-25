# Étape 3 — Prévisions Temporelles (Prophet)

Le script `matrisk_step3_forecast.py` est le module d'anticipation. Il ne regarde pas seulement l'état actuel d'un fournisseur, il prédit son comportement dans les 90 prochains jours (3 mois) en analysant l'historique généré à l'Étape 1.

## 1. Objectif Principal

* **Projeter l'avenir** : Prédire l'évolution du score SRI (Supply Risk Index) à J+30 et J+90.
* **Granularité** : Les prévisions sont faites au niveau macro (Fournisseur) et au niveau micro (Matériau).
* **Alerter** : Détecter les fournisseurs qui semblent corrects aujourd'hui, mais dont la tendance montre qu'ils vont franchir la zone critique (SRI < 40) très bientôt.

## 2. Le Moteur Prophet (Facebook/Meta)

MatriskAI utilise **Prophet**, un modèle de prévision de séries temporelles open-source développé par Meta, particulièrement adapté aux données métiers présentant des tendances non linéaires.

* **Modèle Bayésien** : Contrairement aux moyennes mobiles classiques, Prophet modélise l'incertitude et génère un intervalle de confiance (`yhat_lower`, `yhat_upper`).
* **Condition d'activation** : Prophet est un modèle lourd. Il est appliqué uniquement sur les entités (fournisseurs) disposant d'un historique suffisamment long et varié (ex: 58 fournisseurs sur 76).
* **Saisonnalité & Tendance** : Il est capable de repérer si un fournisseur se dégrade structurellement ou s'il subit juste une variation ponctuelle.

## 3. Le Fallback Linéaire (Correctif v4.2)

Que se passe-t-il si un fournisseur n'a que 2 mois d'historique, ou si son SRI est resté strictement bloqué à 100 pendant 6 mois (zéro variance) ?

```{warning} L'Erreur Stan (v4.1)
L'implémentation originelle plantait (Crash `Stan initialization error`) lorsque Prophet tentait de modéliser une série temporelle parfaitement plate (variance = 0), car son moteur mathématique ne convergeait pas.
```

**Solution v4.2 (Smart Fallback)** : Le système calcule la variance des données avant d'appeler Prophet (`nunique() <= 1`). 
* Si la série est constante ou trop courte : Le système by-pass Prophet.
* **Action** : Il applique automatiquement une régression linéaire simple (qui retourne une droite plate pour une variance nulle), empêchant le pipeline de crasher.

## 4. Seuils & Alertes J+90

Le modèle classe les fournisseurs selon le SRI prédit à 90 jours :

* 🔴 **URGENT (SRI < 40)** : Le fournisseur va défaillir. (Ex: 7 fournisseurs identifiés).
* 🟡 **ATTENTION (40 <= SRI < 65)** : Zone d'incertitude, dégradation en cours. (Ex: 13 fournisseurs).
* 🟢 **OK (SRI >= 65)** : Stable et sécurisé. (Ex: 56 fournisseurs).

```{image} _static/images/sri_score.png
:alt: Distribution des scores SRI
:width: 80%
:align: center
```
*Le système traque la distribution du SRI actuel vs la distribution projetée.*

## 5. Exécution & Outputs

**Commande de lancement :**
```bash
python matrisk_step3_forecast.py
```

**Fichiers générés :**
* `step3_forecast_fournisseurs.csv` : Tendances agrégées par SupplierName.
* `step3_forecast_materiaux.csv` : Tendances unitaires par code matériel.

```{note}
**Phase de "Warm-up"** : Prophet devient véritablement pertinent à partir de la génération du **4ème snapshot mensuel** dans le dossier `Snapshots/`. Avant cela, c'est le fallback linéaire qui assure la stabilité.
```
