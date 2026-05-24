<div align="center">

<img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white"/>
<img src="https://img.shields.io/badge/XGBoost-2.0%2B-E8563B?style=for-the-badge"/>
<img src="https://img.shields.io/badge/Groq-LLaMA_3.3-7C3AED?style=for-the-badge"/>
<img src="https://img.shields.io/badge/version-4.1-4ade80?style=for-the-badge"/>

# 🧑‍💻 MatriskAI
### Supply Chain Risk Intelligence

**Détection · Prévision · Prescription des risques fournisseurs**  
Pipeline ML end-to-end · Dashboard interactif · Chatbot IA intégré

</div>

---

## ✨ Ce que fait MatriskAI

MatriskAI transforme votre **QML Report by Plant** (fichier Excel brut) en intelligence opérationnelle :

| Ce que vous avez | Ce que MatriskAI produit |
|---|---|
| Fichier Excel fournisseurs/matériaux | Score SRI 0–100 par matériau |
| Statuts QML / ASL disparates | Classification ML : 🔴 Élevé / 🟡 Moyen / 🟢 Faible |
| Données ponctuelles | Prévisions J+30 / J+90 (Prophet) |
| Risques non priorisés | Plan d'actions avec dates limites |
| Données brutes | Dashboard interactif + chatbot IA |

---

## 🏗️ Architecture du pipeline

```
📄 QML Report by Plant.xlsx
         │
         ▼
┌─────────────────────────────────┐
│  STEP 1 — Nettoyage & Features  │  → dataset_clean.csv
│  Feature Engineering + SRI      │  → historique_sri.csv (snapshot mensuel)
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  STEP 2 — XGBoost + SHAP        │  → step2_predictions.csv
│  Calibration · Anomalies IA     │  → xgb_model.pkl
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  STEP 3 — Forecast Prophet      │  → step3_forecast_fournisseurs.csv
│  Time Series J+30 / J+90        │  → step3_forecast_materiaux.csv
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  STEP 4 — Moteur Prescriptif    │  → step4_plan_actions.csv
│  15 règles · P1/P2/P3           │  → step4_resume_executif.txt
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  STEP 5 — Dashboard Streamlit   │  Interface web interactive
│  + Chatbot Groq LLaMA 3.3       │  + Assistant flottant 🧑‍💻
└─────────────────────────────────┘
```

---

## 🚀 Démarrage rapide

### 1. Cloner le repo

```bash
git clone https://github.com/votre-org/matrisk-ai.git
cd matrisk-ai
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt

# Prophet est optionnel mais recommandé (meilleurs forecasts dès 4 snapshots)
pip install prophet
```

### 3. Lancer le pipeline complet

```bash
python run_pipeline.py
```

> Lance automatiquement Step 1 → 2 → 3 → 4. Comptez ~30 secondes.

### 4. Ouvrir le dashboard

```bash
streamlit run Scripts/matrisk_step5_dashboard.py
```

Ouvrez `http://localhost:8501` dans votre navigateur. Le chatbot IA est **prêt sans configuration** (clé API intégrée).

---

## 📁 Structure du projet

```
MatriskAI/
│
├── 📄 config.py                    ← Configuration centrale (chemins, features, seuils)
├── 🚀 run_pipeline.py              ← Lanceur pipeline (Steps 1→4)
│
├── 🔧 matrisk_step1_cleaning.py    ← Nettoyage + Feature Engineering + SRI
├── 🤖 matrisk_step2_train.py       ← XGBoost + Calibration + SHAP + Anomalies
├── 📈 matrisk_step3_forecast.py    ← Time Series (Prophet / projection linéaire)
├── 📋 matrisk_step4_prescriptif.py ← Moteur prescriptif 15 règles
│
├── Scripts/
│   └── 🖥️ matrisk_step5_dashboard.py ← Dashboard Streamlit + Chatbot Groq
│
├── Fichiers Excel/                 ← ⚠️ Données — ignorées par Git
│   ├── QML report by Plant.xlsx   ← VOTRE FICHIER D'ENTRÉE
│   ├── dataset_clean.csv          ← Généré par Step 1
│   └── step2_predictions.csv      ← Généré par Step 2
│
├── Snapshots/                      ← Historique mensuel (auto-généré)
├── Logs/                           ← Logs de chaque step
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🧠 Le Score SRI expliqué

Le **Supply Risk Index (SRI)** est calculé sur 0–100 à chaque exécution de Step 1 :

```
SRI = 100
    − (QML×0.6 + ASL×0.4) / 4 × 40    ← statut qualité/fournisseur (max −40)
    − shelf_life_risk / 3 × 25          ← urgence péremption         (max −25)
    − text_risk_flag.clip(3) / 3 × 20   ← signaux NLP dans les notes (max −20)
    + has_ecertificate × 10             ← bonus e-certificat         (+10)
    + has_subplant_backup × 5           ← bonus fournisseur alternatif (+5)
```

| SRI | Niveau | Action |
|---|---|---|
| ≥ 65 | 🟢 **Faible** | Surveillance normale |
| 40–64 | 🟡 **Moyen** | Audit planifié |
| < 40 | 🔴 **Élevé** | Action immédiate |

---

## 🖥️ Dashboard — Pages disponibles

| Page | Contenu |
|---|---|
| **Vue Globale** | KPIs, distribution, heatmap fournisseurs, top 10 risques + accès chatbot |
| **Données & Pipeline** | Upload Excel, déclenchement pipeline, état des fichiers |
| **Time Series IA** | SRI global, anomalies, évolution par fournisseur |
| **Prévisions J+90** | Forecasts Prophet, scatter actuel vs futur |
| **Plan d'Actions** | Actions filtrables P1/P2/P3, export CSV |
| **Explainability SHAP** | Importance des features, beeswarm |
| **Anomalies** | Matériaux détectés par IsolationForest |
| **Simulateur What-If** | Simulation de scénarios en temps réel |
| **🧑‍💻 Assistant IA** | Chatbot Groq LLaMA 3.3 avec contexte dashboard complet |

> **Widget flottant 🧑‍💻** disponible sur toutes les pages — accès instantané au chatbot.

---

## ⚡ Commandes utiles

```bash
# Pipeline complet
python run_pipeline.py

# Étapes sélectives
python run_pipeline.py --steps 134       # Steps 1, 3 et 4 seulement
python run_pipeline.py --steps 24        # Réentraîner ML + plan d'actions

# Avec un fichier Excel custom
python matrisk_step1_cleaning.py --fichier /chemin/vers/mon_fichier.xlsx

# Dashboard avec fichier custom (noter le -- obligatoire)
streamlit run Scripts/matrisk_step5_dashboard.py -- --fichier /chemin/vers/mon.xlsx

# Vérifier les logs
tail -f Logs/step2_train.log
```

---

## 🔄 Mise à jour mensuelle

```bash
# 1. Remplacez le fichier Excel dans Fichiers Excel/
# 2. Relancez le pipeline
python run_pipeline.py

# Step 1 crée automatiquement un nouveau snapshot → historique s'enrichit
# Prophet s'active automatiquement dès 4 snapshots (meilleure précision)
```

---

## 🛠️ Configuration avancée

Tous les paramètres sont dans **`config.py`** :

```python
# Ajuster les seuils SRI
SRI_THRESHOLDS = {
    "Faible": 65,   # SRI ≥ 65 → Faible
    "Moyen" : 40,   # SRI ≥ 40 → Moyen
    # SRI < 40      → Élevé
}

# Ajouter/retirer des features ML
ML_FEATURES = [
    "qml_risk_score",
    "asl_risk_score",
    "combined_risk_score",
    # ...
]
```

---

## 🐛 Bugs connus et fixes (v4.1)

| # | Fichier | Bug | Fix |
|---|---|---|---|
| 1 | `requirements.txt` | `requests` manquant → chatbot crash | Ajout `requests>=2.31.0` |
| 2 | `step2_train.py` | `cv=3` échoue si classe < 3 samples | `cv` adaptatif `min(3, max(2, n))` |
| 3 | `step2_train.py` | `UndefinedMetricWarning` dans les logs | `zero_division=0` dans `classification_report` |
| 4 | `dashboard.py` | `sys.argv` cassé sous Streamlit | Parse args après séparateur `--` |
| 5 | `dashboard.py` | Double appel API Groq | Reset `pending_reply=False` au clic |
| 6 | `dashboard.py` | `st.image()` ternaire → DeltaGenerator affiché | Remplacement par `if/else` classique |

---

## 📦 Dépendances

```
pandas>=2.0.0       numpy>=1.24.0       openpyxl>=3.1.0
xgboost>=2.0.0      scikit-learn>=1.3.0  shap>=0.44.0
streamlit>=1.30.0   plotly>=5.18.0      matplotlib>=3.7.0
joblib>=1.3.0       requests>=2.31.0
prophet>=1.1.5      (optionnel)
```

---

## 🤝 Contribuer

Consultez [CONTRIBUTING.md](CONTRIBUTING.md) pour le workflow Git, les conventions de commits et les règles de sécurité des données.

---

<div align="center">

**MatriskAI v4.1** · Supply Chain Risk Intelligence  
Pipeline : Nettoyage → XGBoost + Calibration → Prophet → Prescriptif → Dashboard + Chatbot Groq

</div>