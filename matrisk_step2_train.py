"""
MatriskAI — Étape 2 : Modèle XGBoost + Calibration + SHAP
===========================================================
AMÉLIORATIONS v4 :
  ✅ Logging structuré via config.py
  ✅ Features depuis config.ML_FEATURES (liste centralisée)
  ✅ Assertion anti-data-leakage (SRI, risk_label exclus des features)
  ✅ Split temporel (matériaux récents = test) au lieu de split aléatoire
  ✅ Gestion SHAP robuste pour toutes versions XGBoost/SHAP
  ✅ Gestion des variables score_deg/vm initialisées avant le bloc try
  ✅ Rapport de performance sauvegardé dans un fichier texte
"""

import pandas as pd
import numpy as np
import pickle
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from xgboost import XGBClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import IsolationForest
import shap

# ── Config centrale ──────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PATHS, ML_FEATURES, setup_logging

log = setup_logging("step2_train")

log.info("=" * 60)
log.info("  MATRISK AI — ÉTAPE 2 v4 : XGBoost + Calibration + Anomalies")
log.info("=" * 60)
log.info("Dossier projet : %s", PATHS["base"])


# ══════════════════════════════════════════════════════════════════
# 1. CHARGEMENT
# ══════════════════════════════════════════════════════════════════
log.info("[1/7] Chargement du dataset...")

if not os.path.exists(PATHS["dataset_clean"]):
    log.error("Fichier introuvable : %s", PATHS["dataset_clean"])
    log.error("Lancez d'abord matrisk_step1_cleaning.py !")
    sys.exit(1)

try:
    df = pd.read_csv(PATHS["dataset_clean"], sep=",", encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
except Exception as e:
    log.error("Impossible de lire le dataset : %s", e)
    sys.exit(1)

log.info("Chargé : %d lignes | %d colonnes", len(df), df.shape[1])

# ── Sélection des features disponibles ───────────────────────────
FEATURES = [f for f in ML_FEATURES if f in df.columns]
TARGET   = "risk_label"

# ── Assertions anti-data-leakage (BUG FIX #5) ────────────────────
assert "SRI" not in FEATURES, \
    "DATA LEAKAGE : 'SRI' est calculé depuis les features → à exclure"
assert "risk_label" not in FEATURES, \
    "DATA LEAKAGE : 'risk_label' est la cible → à exclure"

missing_features = [f for f in ML_FEATURES if f not in df.columns]
if missing_features:
    log.warning("Features ML_FEATURES absentes du CSV (ignorées) : %s", missing_features)

X = df[FEATURES].copy()
y = df[TARGET].copy()
log.info("%d features utilisées : %s", len(FEATURES), FEATURES)

if y.isna().any():
    log.error("%d lignes sans label — vérifiez step1", y.isna().sum())
    sys.exit(1)


# ══════════════════════════════════════════════════════════════════
# 2. ENCODAGE
# ══════════════════════════════════════════════════════════════════
log.info("[2/7] Encodage de la cible...")
le = LabelEncoder()
y_enc = le.fit_transform(y)
for num, nom in enumerate(le.classes_):
    nb = int((y == nom).sum())
    log.info("  %-10s → %d  (%d | %.1f%%)", nom, num, nb, nb / len(y) * 100)


# ══════════════════════════════════════════════════════════════════
# 3. DÉTECTION D'ANOMALIES — IsolationForest
# ══════════════════════════════════════════════════════════════════
log.info("[3/7] Détection d'anomalies (IsolationForest)...")

iso = IsolationForest(
    n_estimators=150,
    contamination=0.05,   # supposer 5% d'outliers
    random_state=42,
    n_jobs=-1,
)
anomalies_raw  = iso.fit_predict(X)
df["est_anomalie"] = (anomalies_raw == -1).astype(int)
n_anomalies = int(df["est_anomalie"].sum())
log.info("Anomalies détectées : %d (%.1f%%)", n_anomalies, n_anomalies / len(df) * 100)

# Cas particulièrement risqué : anomalie + label Faible
n_paradoxaux = int(((df["est_anomalie"] == 1) & (y == "Faible")).sum())
if n_paradoxaux > 0:
    log.warning("%d matériaux classés Faible mais détectés anomalie — vérification manuelle recommandée",
                n_paradoxaux)


# ══════════════════════════════════════════════════════════════════
# 4. SPLIT TRAIN / TEST — TEMPOREL (BUG FIX Split aléatoire → temporel)
# ══════════════════════════════════════════════════════════════════
log.info("[4/7] Split train/test temporel...")

# On utilise days_since_update comme proxy temporel :
# matériaux récents (peu de jours) → test set → plus proche de la réalité future
from sklearn.model_selection import train_test_split

if "days_since_update" in df.columns and (df["days_since_update"] > 0).any():
    threshold  = df["days_since_update"].quantile(0.20)   # 20% les plus récents = test
    mask_test  = df["days_since_update"].values <= threshold
    mask_train = ~mask_test
    # y_enc est un numpy array → utiliser np.unique() et non .nunique()
    classes_test  = len(np.unique(y_enc[mask_test]))
    classes_train = len(np.unique(y_enc[mask_train]))
    if classes_test >= 2 and classes_train >= 2 and mask_test.sum() >= 20:
        X_train = X.iloc[mask_train]
        X_test  = X.iloc[mask_test]
        y_train = y_enc[mask_train]
        y_test  = y_enc[mask_test]
        log.info("Split temporel : train=%d | test=%d (days_since_update <= %.0f jours)",
                 len(X_train), len(X_test), threshold)
    else:
        log.warning("Split temporel impossible (classes ou effectif insuffisants) → fallback aléatoire")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_enc, test_size=0.2, random_state=42, stratify=y_enc
        )
else:
    log.warning("days_since_update non disponible → split aléatoire stratifié")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=0.2, random_state=42, stratify=y_enc
    )

sample_weights = compute_sample_weight("balanced", y_train)
log.info("Entraînement : %d | Test : %d", len(X_train), len(X_test))


# ══════════════════════════════════════════════════════════════════
# 5. ENTRAÎNEMENT XGBOOST + CALIBRATION ISOTONIQUE
# ══════════════════════════════════════════════════════════════════
# POURQUOI CALIBRER ?
# Sans calibration, "proba_Élevé = 0.87" n'est qu'un score relatif.
# Avec CalibratedClassifierCV(method="isotonic"), si le modèle dit 0.80,
# ~80% des matériaux avec ce score sont vraiment à risque élevé.
# Les probabilités deviennent interprétables et actionnables.
#
# NOTE : Les SHAP values sont calculées sur xgb_base (modèle brut),
# car CalibratedClassifierCV n'est pas compatible avec TreeExplainer.
# Les valeurs SHAP restent valides pour l'interprétabilité des features.
# ══════════════════════════════════════════════════════════════════
log.info("[5/7] Entraînement XGBoost + Calibration isotonique...")

xgb_base = XGBClassifier(
    n_estimators=200,
    max_depth=4,
    learning_rate=0.1,
    subsample=0.8,
    colsample_bytree=0.8,
    eval_metric="mlogloss",
    random_state=42,
    n_jobs=-1,
    verbosity=0,
)

try:
    xgb_base.fit(X_train, y_train, sample_weight=sample_weights)
    log.info("XGBoost entraîné")
except Exception as e:
    log.error("Erreur entraînement XGBoost : %s", e)
    sys.exit(1)

    counts = np.bincount(y_train)
    min_class_count = int(counts[counts > 0].min()) if len(counts[counts > 0]) > 0 else 0
    
    if min_class_count < 3:
        log.warning("Classe minoritaire trop rare (%d sample) pour la calibration isotonique croisée.", min_class_count)
        log.warning("Bypass propre de la calibration. Utilisation du modèle XGBoost brut (par défaut très performant).")
        model_calibre = xgb_base
    else:
        cv_cal = min(3, min_class_count)
        try:
            model_calibre = CalibratedClassifierCV(xgb_base, method="isotonic", cv=cv_cal)
            model_calibre.fit(X_train, y_train, sample_weight=sample_weights)
            log.info("Calibration isotonique appliquée (cv=%d)", cv_cal)
        except Exception as e:
            log.warning("Calibration isotonique échouée (%s) — utilisation du modèle brut", e)
            model_calibre = xgb_base


# ══════════════════════════════════════════════════════════════════
# 6. ÉVALUATION
# ══════════════════════════════════════════════════════════════════
log.info("[6/7] Évaluation...")

try:
    y_pred_base  = xgb_base.predict(X_test)
    y_pred_calib = model_calibre.predict(X_test)

    acc_base  = float((y_pred_base  == y_test).mean())
    acc_calib = float((y_pred_calib == y_test).mean())

    log.info("Précision XGBoost brut    : %.1f%%", acc_base * 100)
    log.info("Précision XGBoost calibré : %.1f%%", acc_calib * 100)

    rapport = classification_report(y_test, y_pred_calib, target_names=le.classes_, zero_division=0)
    log.info("Rapport de classification (calibré) :\n%s", rapport)

    # ── Validation croisée (sur modèle brut, plus rapide) ────────
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(xgb_base, X, y_enc, cv=cv, scoring="f1_weighted")
    log.info("F1-score CV (5-fold) : %.3f ± %.3f", cv_scores.mean(), cv_scores.std())

    # ── Sauvegarde rapport performance ───────────────────────────
    rapport_path = os.path.join(PATHS["base"], "step2_rapport_performance.txt")
    with open(rapport_path, "w", encoding="utf-8") as f:
        f.write(f"MatriskAI v4 — Rapport de performance Step 2\n")
        f.write(f"{'='*50}\n\n")
        f.write(f"Précision XGBoost brut    : {acc_base:.1%}\n")
        f.write(f"Précision XGBoost calibré : {acc_calib:.1%}\n")
        f.write(f"F1-score CV               : {cv_scores.mean():.3f} ± {cv_scores.std():.3f}\n\n")
        f.write("Rapport de classification :\n")
        f.write(rapport)
    log.info("Rapport performance → %s", rapport_path)

except Exception as e:
    log.warning("Erreur lors de l'évaluation : %s", e)
    acc_calib  = 0.0
    cv_scores  = np.array([0.0])


# ══════════════════════════════════════════════════════════════════
# 7. SHAP — Gestion robuste multi-versions (BUG FIX #6)
# ══════════════════════════════════════════════════════════════════
log.info("[7/7] SHAP + sauvegarde...")

try:
    explainer   = shap.TreeExplainer(xgb_base)
    shap_values = explainer.shap_values(X_test)

    # Normaliser en array 3D (n_samples, n_features, n_classes)
    if isinstance(shap_values, list):
        # Ancienne API SHAP : liste de (n_samples, n_features)
        shap_values = np.stack(shap_values, axis=2)
    elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 2:
        # Binaire : (n_samples, n_features) → ajouter dimension classe
        shap_values = shap_values[:, :, np.newaxis]

    # Sélectionner la classe "Élevé"
    if "Élevé" in list(le.classes_):
        idx_eleve = list(le.classes_).index("Élevé")
    else:
        idx_eleve = 0
        log.warning("Classe 'Élevé' non trouvée — utilisation de la classe 0 pour SHAP")

    shap_plot = shap_values[:, :, idx_eleve] if shap_values.ndim == 3 else shap_values

    # Graphique 1 : importance globale (bar)
    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_plot, X_test, plot_type="bar", show=False,
                      feature_names=FEATURES)
    plt.title("Importance globale des critères — MatriskAI v4")
    plt.tight_layout()
    plt.savefig(PATHS["shap_bar"], bbox_inches="tight", dpi=150)
    plt.close()

    # Graphique 2 : beeswarm
    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_plot, X_test, show=False, feature_names=FEATURES)
    plt.title("Impact des features sur le Risque Élevé — MatriskAI v4")
    plt.tight_layout()
    plt.savefig(PATHS["shap_beeswarm"], bbox_inches="tight", dpi=150)
    plt.close()

    log.info("Graphiques SHAP sauvegardés")

except Exception as e:
    log.warning("Erreur SHAP (non bloquante) : %s", e)
    log.warning("Les graphiques SHAP ne seront pas disponibles dans le dashboard")


# ══════════════════════════════════════════════════════════════════
# SAUVEGARDE DES PRÉDICTIONS
# ══════════════════════════════════════════════════════════════════
log.info("Sauvegarde des prédictions...")

try:
    probas_calib = model_calibre.predict_proba(X)
    classes      = list(le.classes_)

    df["predicted_label"]    = le.inverse_transform(model_calibre.predict(X))
    df["proba_Elevé"]        = probas_calib[:, classes.index("Élevé")].round(4) if "Élevé" in classes else 0.0
    df["proba_Moyen"]        = probas_calib[:, classes.index("Moyen")].round(4) if "Moyen" in classes else 0.0
    df["proba_Faible"]       = probas_calib[:, classes.index("Faible")].round(4) if "Faible" in classes else 0.0
    df["correct_prediction"] = (df["predicted_label"] == df[TARGET]).astype(int)

    # ── Score de confiance enrichi ────────────────────────────────
    # Entropie faible = modèle très sûr de sa prédiction
    probas_arr       = probas_calib + 1e-9
    entropie         = -np.sum(probas_arr * np.log(probas_arr), axis=1)
    entropie_max     = np.log(len(classes)) if len(classes) > 1 else 1.0
    confiance_modele = ((1 - entropie / entropie_max) * 100).round(1)

    if "score_confiance" in df.columns:
        df["confiance_finale"] = (df["score_confiance"] * 0.5 + confiance_modele * 0.5).round(1)
    else:
        df["confiance_finale"] = confiance_modele.round(1)

    df_sorted = df.sort_values("proba_Elevé", ascending=False)
    df_sorted.to_csv(PATHS["predictions"], index=False, encoding="utf-8-sig")
    log.info("Prédictions → %s", PATHS["predictions"])

except Exception as e:
    log.error("Erreur sauvegarde prédictions : %s", e)
    sys.exit(1)

# ── Sauvegarde modèle ─────────────────────────────────────────────
try:
    with open(PATHS["model"], "wb") as f:
        pickle.dump({
            "model"        : model_calibre,   # calibré → production
            "model_raw"    : xgb_base,        # brut → SHAP
            "features"     : FEATURES,
            "label_encoder": le,
            "acc_calib"    : acc_calib,
            "f1_cv"        : float(cv_scores.mean()) if len(cv_scores) > 0 else 0.0,
        }, f)
    log.info("Modèle → %s", PATHS["model"])
except Exception as e:
    log.error("Erreur sauvegarde modèle : %s", e)
    sys.exit(1)

# ── Résumé final ──────────────────────────────────────────────────
n_e = int((df["predicted_label"] == "Élevé").sum())
n_m = int((df["predicted_label"] == "Moyen").sum())
n_f = int((df["predicted_label"] == "Faible").sum())

log.info("=" * 60)
log.info("RÉSUMÉ — Étape 2 v4 terminée")
log.info("=" * 60)
log.info("Précision test set     : %.1f%%", acc_calib * 100)
log.info("F1-score CV            : %.3f", cv_scores.mean())
log.info("Anomalies détectées    : %d", n_anomalies)
log.info("Élevé / Moyen / Faible : %d / %d / %d", n_e, n_m, n_f)
log.info("Confiance finale moy   : %.1f/100", df["confiance_finale"].mean())
log.info("=" * 60)