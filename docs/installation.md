# Installation & Configuration

> [!TIP]
> **Vous préférez utiliser l'application sans l'installer ?**
> MatriskAI est disponible directement en ligne en mode SaaS sécurisé. Vous pouvez charger vos propres données et analyser vos fournisseurs sans configuration :
> 👉 **Accéder à l'application Cloud :** [matriskai.streamlit.app](https://matriskai.streamlit.app)
> Pour en savoir plus sur ce mode de fonctionnement, consultez la page [Déploiement Cloud & SaaS](deploiement.md).

---

## 1. Prérequis Système

Pour faire tourner MatriskAI sur votre machine locale (développement/exécution locale), vous avez besoin de :

* **Python 3.9 ou supérieur** (testé sur 3.10 et 3.11).
* **Git** (pour cloner le dépôt).
* **pip** (gestionnaire de paquets Python).
* *(Optionnel mais recommandé)* **Docker Desktop** (si vous souhaitez lancer l'application conteneurisée sans installer Python localement).

## 2. Installation Locale (Standard)

Ouvrez votre terminal (Invite de commandes, PowerShell, ou Terminal macOS/Linux) et exécutez les commandes suivantes :

```bash
# 1. Cloner le projet depuis GitHub
git clone https://github.com/intissarlayad/MatriskAI.git
cd MatriskAI

# 2. Créer un environnement virtuel isolé (recommandé)
python -m venv venv

# 3. Activer l'environnement virtuel
# Sur Windows :
venv\Scripts\activate
# Sur Linux / macOS :
source venv/bin/activate

# 4. Installer les dépendances principales
pip install -r requirements.txt

# 5. Installer Prophet (souvent capricieux sur Windows, à installer séparément si erreur)
pip install prophet
```

## 3. Configuration de l'Environnement

Le projet repose sur deux fichiers de configuration essentiels :

### A. Le fichier `.env` (Sécurité API)
Pour utiliser le chatbot de l'Étape 5 (Dashboard), vous devez configurer la clé API Groq.
1. Créez un fichier texte nommé exactement `.env` à la racine du projet.
2. Ajoutez cette ligne à l'intérieur :
   ```text
   GROQ_API_KEY=gsk_VotreCleApiIci
   ```
```{note}
Le fichier `.gitignore` est déjà configuré pour ignorer le fichier `.env`. Vos clés secrètes ne seront jamais envoyées sur GitHub.
```

### B. Le fichier `config.py` (Cerveau du projet)
Ce fichier (à la racine) contrôle absolument tous les paramètres du pipeline :
* `PATHS` : Chemins dynamiques vers les dossiers (`Fichiers Excel`, `Snapshots`, `Logs`). Ne nécessite aucune modification entre Windows/Mac.
* `ML_FEATURES` : La liste exacte des 10 variables autorisées pour XGBoost.
* `SRI_THRESHOLDS` : Les seuils de décision (actuellement 65 pour Faible, 40 pour Moyen).
* `COL_CANDIDATES` : Un dictionnaire intelligent permettant au système de retrouver les colonnes Excel même si l'ERP change leur orthographe (ex: `PartNumber` vs `Code`).

## 4. Exécution du Projet

Vous avez deux manières d'exécuter MatriskAI.

**Option A : Lancement automatisé (End-to-End)**
Exécutez le script maître qui lancera les étapes 1 à 4 dans le bon ordre, avec gestion des erreurs :
```bash
python run_pipeline.py
```

**Option B : Lancement manuel étape par étape (Debugging)**
```bash
python matrisk_step1_cleaning.py
python matrisk_step2_train.py
python matrisk_step3_forecast.py
python matrisk_step4_prescriptif.py
```

**Pour lancer l'interface graphique (Dashboard) :**
```bash
streamlit run Scripts/matrisk_step5_dashboard.py
```

## 5. Déploiement Docker (Avancé)

Si vous rencontrez des problèmes d'installation Python (conflits de librairies), MatriskAI est "Docker-ready". Docker crée une machine virtuelle légère contenant exactement ce qu'il faut pour faire tourner l'app.

```bash
# Construire l'image Docker (cela prend quelques minutes la première fois)
docker build -t matrisk-ai .

# Lancer le conteneur en attachant le port 8501 et le fichier .env
docker run -p 8501:8501 --env-file .env matrisk-ai
```
Ouvrez ensuite `http://localhost:8501` dans votre navigateur.

## 6. Documentation Locale (Sphinx)

Si vous souhaitez modifier et regénérer ce site web documentaire (celui que vous lisez actuellement) :

```bash
cd docs
pip install -r requirements.txt  # installe Sphinx et MyST
sphinx-build -b html . _build/html
```
Ouvrez ensuite le fichier `docs/_build/html/index.html` dans votre navigateur.
