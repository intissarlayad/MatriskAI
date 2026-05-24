"""
MatriskAI — Configuration centrale
====================================
Tous les chemins, paramètres et constantes du pipeline sont ici.
Importez ce fichier depuis chaque script :
    from config import PATHS, ML_FEATURES, SRI_THRESHOLDS, setup_logging
"""

import os
import logging
import sys

# ── Force l'encodage UTF-8 pour la console Windows afin d'éviter les crashs de symboles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
# CHEMINS
# ══════════════════════════════════════════════════════════════════
# config.py doit être placé à la RACINE du projet (même niveau que Fichiers Excel/)
BASE_PATH = os.path.dirname(os.path.abspath(__file__))

PATHS = {
    "base"          : BASE_PATH,
    "excel_dir"     : os.path.join(BASE_PATH, "Fichiers Excel"),
    "snapshots_dir" : os.path.join(BASE_PATH, "Snapshots"),
    "logs_dir"      : os.path.join(BASE_PATH, "Logs"),
    # Entrée
    "input_excel"   : os.path.join(BASE_PATH, "Fichiers Excel", "QML report by Plant (27).xlsx"),
    # Outputs Step 1
    "dataset_clean" : os.path.join(BASE_PATH, "Fichiers Excel", "dataset_clean.csv"),
    "historique"    : os.path.join(BASE_PATH, "historique_sri.csv"),
    # Outputs Step 2
    "predictions"   : os.path.join(BASE_PATH, "Fichiers Excel", "step2_predictions.csv"),
    "model"         : os.path.join(BASE_PATH, "xgb_model.pkl"),
    "shap_bar"      : os.path.join(BASE_PATH, "shap_importance_bar.png"),
    "shap_beeswarm" : os.path.join(BASE_PATH, "shap_beeswarm_eleve.png"),
    # Outputs Step 3
    "forecast_fourn": os.path.join(BASE_PATH, "step3_forecast_fournisseurs.csv"),
    "forecast_mat"  : os.path.join(BASE_PATH, "step3_forecast_materiaux.csv"),
    # Outputs Step 4
    "plan_actions"  : os.path.join(BASE_PATH, "step4_plan_actions.csv"),
    "resume_exec"   : os.path.join(BASE_PATH, "step4_resume_executif.txt"),
}

# Créer les dossiers manquants au démarrage
for folder in ["excel_dir", "snapshots_dir", "logs_dir"]:
    os.makedirs(PATHS[folder], exist_ok=True)

# ══════════════════════════════════════════════════════════════════
# FEATURES ML
# ══════════════════════════════════════════════════════════════════
# ⚠️ NE PAS inclure "SRI" ni "risk_label" — data leakage garanti
ML_FEATURES = [
    "qml_risk_score",
    "asl_risk_score",
    "combined_risk_score",
    "days_since_update",
    "shelf_life_risk",
    "has_ecertificate",
    "has_subplant_backup",
    "text_risk_flag",
    "vitesse_degradation",
    "date_inconnue",       # ← nouveau : flag explicite pour date manquante
]

# ══════════════════════════════════════════════════════════════════
# SEUILS SRI
# ══════════════════════════════════════════════════════════════════
SRI_THRESHOLDS = {
    "Faible": 65,    # SRI >= 65  → Faible
    "Moyen" : 40,    # SRI >= 40  → Moyen
    # SRI < 40  → Élevé
}

# ══════════════════════════════════════════════════════════════════
# ENCODAGES
# ══════════════════════════════════════════════════════════════════
QML_MAP = {
    "C:Certified"      : 0,
    "Q:Qualified"      : 1,
    "I:Initiation"     : 2,
    "X:Created by DMS" : 2,
    "O:Obsolete"       : 3,
    "D:Disqualified"   : 4,
}

ASL_MAP = {
    "A:Approved"    : 0,
    "W:Waived"      : 1,
    "I:Initiation"  : 2,
    "P:Probation"   : 3,
    "D:Disapproved" : 4,
}

# ══════════════════════════════════════════════════════════════════
# NOMS DE COLONNES (liste de candidats par priorité)
# ══════════════════════════════════════════════════════════════════
COL_CANDIDATES = {
    "code"       : ["STMaterialCode", "MaterialCode", "Code", "PartNumber"],
    "fournisseur": ["supplierHoldingName", "MfgName", "Manufacturer", "SupplierName"],
    "nlp"        : ["Summary of change NLP", "Summary of change",
                    "Summary Of Change NLP", "Summary Of Change"],
    "shelf_life" : ["remainingShelfLife(Months)", "ShelfLifeMonths", "shelf_life"],
    "updated"    : ["Updated date", "UpdatedDate", "Last Updated"],
    "qml_status" : ["QML Status", "QMLStatus", "QML_Status"],
    "asl_status" : ["ASLStatus", "ASL Status", "ASL_Status"],
    "description": ["STMaterialDesc", "MaterialDescription", "Description", "Desc", "Designation"],
}

def detect_column(df_columns, key):
    """
    Détecte la première colonne correspondant à une clé de COL_CANDIDATES.
    Retourne None si aucune correspondance.
    """
    candidates = COL_CANDIDATES.get(key, [])
    for c in candidates:
        if c in df_columns:
            return c
    # Fallback : recherche partielle insensible à la casse
    key_lower = key.lower()
    for col in df_columns:
        if key_lower in col.lower():
            return col
    return None

# ══════════════════════════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════════════════════════
def setup_logging(script_name: str) -> logging.Logger:
    """
    Configure et retourne un logger nommé pour le script donné.
    Écrit dans Logs/<script_name>.log ET dans la console.
    """
    log_file = os.path.join(PATHS["logs_dir"], f"{script_name}.log")
    logger = logging.getLogger(script_name)
    logger.setLevel(logging.DEBUG)

    # Éviter les handlers en double si le logger est déjà configuré
    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler fichier
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    # Handler console
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger
