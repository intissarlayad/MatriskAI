"""
MatriskAI — Étape 3 : Prévision Time Series avec Prophet
=========================================================
AMÉLIORATIONS v4 :
  ✅ Logging structuré via config.py
  ✅ Unpacking forecast_lineaire corrigé (plus fragile)
  ✅ score_deg et vm initialisés avant le bloc try (BUG FIX)
  ✅ Règle clustering nettoyée (emojis dans les valeurs supprimés pour les filtres)
  ✅ Gestion d'erreur Prophet par fournisseur + log détaillé
  ✅ Nouvelles règles clustering : single-source + dégradation confirmée

LOGIQUE :
  Si historique ≥ 4 snapshots ET Prophet installé → Forecast Prophet
  Sinon → Projection linéaire (fallback robuste)
"""

import pandas as pd
import numpy as np
import os
import sys
import warnings
warnings.filterwarnings("ignore")

# ── Config centrale ──────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PATHS, SRI_THRESHOLDS, setup_logging

log = setup_logging("step3_forecast")

log.info("=" * 60)
log.info("  MATRISK AI — ÉTAPE 3 v4 : Time Series + Prophet")
log.info("=" * 60)
log.info("Dossier projet : %s", PATHS["base"])


# ══════════════════════════════════════════════════════════════════
# 0. VÉRIFICATION PROPHET
# ══════════════════════════════════════════════════════════════════
PROPHET_DISPONIBLE = False
try:
    from prophet import Prophet
    PROPHET_DISPONIBLE = True
    log.info("Prophet détecté — Forecasting avancé activé")
except ImportError:
    log.warning("Prophet non installé → Projection linéaire utilisée")
    log.warning("Pour activer Prophet : pip install prophet")


# ══════════════════════════════════════════════════════════════════
# 1. CHARGEMENT DES DONNÉES
# ══════════════════════════════════════════════════════════════════
log.info("[1/6] Chargement des données...")

if not os.path.exists(PATHS["predictions"]):
    log.error("Fichier introuvable : %s", PATHS["predictions"])
    log.error("Lancez d'abord matrisk_step2_train.py !")
    sys.exit(1)

try:
    df = pd.read_csv(PATHS["predictions"], sep=",", encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
except Exception as e:
    log.error("Impossible de lire les prédictions : %s", e)
    sys.exit(1)

log.info("Matériaux chargés : %d", len(df))

# ── Chargement historique ─────────────────────────────────────────
historique    = None
nb_snapshots  = 0

if os.path.exists(PATHS["historique"]):
    try:
        historique = pd.read_csv(PATHS["historique"], encoding="utf-8-sig")
        historique["date"] = pd.to_datetime(historique["date"])
        nb_snapshots = historique["date"].nunique()
        log.info("Historique chargé : %d snapshot(s) (%s → %s)",
                 nb_snapshots,
                 historique["date"].min().strftime("%Y-%m-%d"),
                 historique["date"].max().strftime("%Y-%m-%d"))
    except Exception as e:
        log.warning("Erreur lecture historique : %s", e)
        historique = None
else:
    log.warning("Pas d'historique — lancez step1 plusieurs fois à des dates différentes")

# ── Détection colonne fournisseur ─────────────────────────────────
from config import detect_column
COLONNE_FOURNISSEUR = detect_column(df.columns, "fournisseur")
if COLONNE_FOURNISSEUR is None:
    # Fallback : prendre la colonne object avec le plus de valeurs uniques
    obj_cols = df.select_dtypes(include="object").columns
    if len(obj_cols) > 0:
        COLONNE_FOURNISSEUR = df[obj_cols].nunique().idxmax()
        log.warning("Colonne fournisseur non trouvée → utilisation de '%s'", COLONNE_FOURNISSEUR)
    else:
        log.error("Aucune colonne fournisseur détectable")
        sys.exit(1)

log.info("Colonne fournisseur : '%s'", COLONNE_FOURNISSEUR)


# ══════════════════════════════════════════════════════════════════
# 2. FONCTIONS DE FORECAST
# ══════════════════════════════════════════════════════════════════

def sri_to_label(s):
    if s >= SRI_THRESHOLDS["Faible"]: return "Faible"
    if s >= SRI_THRESHOLDS["Moyen"]:  return "Moyen"
    return "Élevé"


def forecast_prophet(historique_fourn, sri_actuel):
    """
    Prévision Prophet pour un fournisseur ayant ≥ 4 snapshots.
    Retourne un dict avec toutes les valeurs prévues.
    """
    from prophet import Prophet
    df_p = (historique_fourn
            .rename(columns={"date": "ds", "SRI": "y"})
            .sort_values("ds")
            .dropna(subset=["y"]))

    if len(df_p) < 2:
        return None  # pas assez de points après nettoyage

    # FIX : Éviter l'erreur d'initialisation Stan si la série temporelle est parfaitement constante
    if df_p["y"].nunique() <= 1:
        return None

    m = Prophet(
        yearly_seasonality=False,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.80,
        changepoint_prior_scale=0.3,
    )
    m.fit(df_p[["ds", "y"]])

    future   = m.make_future_dataframe(periods=90, freq="D")
    forecast = m.predict(future)

    future_only = forecast[forecast["ds"] > df_p["ds"].max()]
    if len(future_only) == 0:
        return None

    j30 = future_only.iloc[min(29, len(future_only) - 1)]
    j90 = future_only.iloc[min(89, len(future_only) - 1)]

    return {
        "sri_j30"       : float(np.clip(j30["yhat"],       0, 100)),
        "sri_j90"       : float(np.clip(j90["yhat"],       0, 100)),
        "sri_j30_lower" : float(np.clip(j30["yhat_lower"], 0, 100)),
        "sri_j90_lower" : float(np.clip(j90["yhat_lower"], 0, 100)),
        "sri_j30_upper" : float(np.clip(j30["yhat_upper"], 0, 100)),
        "sri_j90_upper" : float(np.clip(j90["yhat_upper"], 0, 100)),
        "methode"       : "prophet",
        "score_deg"     : None,
        "vm"            : None,
    }


def forecast_lineaire(groupe):
    """
    Projection linéaire basée sur le score de dégradation.
    Fallback si Prophet indisponible ou historique insuffisant.
    Retourne un dict avec toutes les valeurs prévues.
    """
    sri_moyen    = groupe["SRI"].mean()
    qml_moyen    = groupe["qml_risk_score"].mean()
    pct_obsolete = (groupe["qml_risk_score"] >= 3).mean()
    anciennete   = groupe["days_since_update"].mean()

    signal_qml        = qml_moyen / 4
    signal_obsolete   = pct_obsolete
    signal_sri        = 1 - (sri_moyen / 100)
    signal_anciennete = min(anciennete / 730, 1) if anciennete > 0 else 0

    score_deg = (signal_qml * 0.35 + signal_obsolete * 0.30 +
                 signal_sri * 0.25 + signal_anciennete * 0.10)

    if   score_deg > 0.7: vm = -2.5
    elif score_deg > 0.5: vm = -1.5
    elif score_deg > 0.3: vm = -0.5
    else:                 vm = +0.3

    sri_j30 = float(np.clip(sri_moyen + vm * 1, 0, 100))
    sri_j90 = float(np.clip(sri_moyen + vm * 3, 0, 100))

    return {
        "sri_j30"       : sri_j30,
        "sri_j90"       : sri_j90,
        "sri_j30_lower" : float(np.clip(sri_j30 - 5,  0, 100)),
        "sri_j90_lower" : float(np.clip(sri_j90 - 10, 0, 100)),
        "sri_j30_upper" : float(np.clip(sri_j30 + 5,  0, 100)),
        "sri_j90_upper" : float(np.clip(sri_j90 + 10, 0, 100)),
        "methode"       : "linéaire",
        "score_deg"     : round(float(score_deg), 3),
        "vm"            : float(vm),
    }


# ══════════════════════════════════════════════════════════════════
# 3. CALCUL DU PROFIL FOURNISSEUR
# ══════════════════════════════════════════════════════════════════
log.info("[2/6] Calcul des profils fournisseurs...")


def calculer_profil_fournisseur(groupe):
    nom_fourn = groupe[COLONNE_FOURNISSEUR].iloc[0]
    n         = len(groupe)
    sri_moyen = float(groupe["SRI"].mean())

    pct_eleve    = float((groupe["predicted_label"] == "Élevé").mean())
    pct_moyen    = float((groupe["predicted_label"] == "Moyen").mean())
    pct_obsolete = float((groupe["qml_risk_score"] >= 3).mean())
    qml_moyen    = float(groupe["qml_risk_score"].mean())
    asl_moyen    = float(groupe["asl_risk_score"].mean())
    has_backup   = int(groupe.get("has_subplant_backup", pd.Series([0])).max()) \
                   if "has_subplant_backup" in groupe.columns else 0

    # ── Choix de la méthode de forecast ──────────────────────────
    nb_pts_historique  = 0
    fiabilite_forecast = 30
    res_forecast       = None

    if historique is not None and PROPHET_DISPONIBLE:
        hist_fourn = historique[historique["fournisseur"].astype(str) == str(nom_fourn)]
        nb_pts_historique = len(hist_fourn)

        if nb_pts_historique >= 4:
            try:
                res_forecast = forecast_prophet(hist_fourn, sri_moyen)
                if res_forecast is not None:
                    fiabilite_forecast = min(50 + nb_pts_historique * 5, 95)
                    log.debug("  Prophet OK pour '%s' (%d pts)", nom_fourn, nb_pts_historique)
                else:
                    log.warning("  Prophet retourné None pour '%s' → fallback linéaire", nom_fourn)
            except Exception as e:
                log.warning("  Erreur Prophet pour '%s' : %s → fallback linéaire", nom_fourn, e)
                res_forecast = None

        if res_forecast is None:
            fiabilite_forecast = 25 + nb_pts_historique * 5
    
    if res_forecast is None:
        res_forecast = forecast_lineaire(groupe)

    # ── Labels ───────────────────────────────────────────────────
    label_actuel = sri_to_label(sri_moyen)
    label_j30    = sri_to_label(res_forecast["sri_j30"])
    label_j90    = sri_to_label(res_forecast["sri_j90"])

    if label_actuel == "Élevé" or label_j30 == "Élevé":
        alerte = "URGENT"
    elif label_j90 == "Moyen" or label_actuel == "Moyen":
        alerte = "ATTENTION"
    else:
        alerte = "OK"

    return {
        "fournisseur"         : nom_fourn,
        "nb_materiaux"        : n,
        "has_backup"          : has_backup,
        "sri_actuel"          : round(sri_moyen, 1),
        "pct_eleve"           : round(pct_eleve * 100, 1),
        "pct_moyen"           : round(pct_moyen * 100, 1),
        "pct_obsolete"        : round(pct_obsolete * 100, 1),
        "qml_moyen"           : round(qml_moyen, 2),
        "asl_moyen"           : round(asl_moyen, 2),
        "score_degradation"   : res_forecast["score_deg"],
        "variation_mensuelle" : res_forecast["vm"],
        "sri_j30"             : round(res_forecast["sri_j30"], 1),
        "sri_j90"             : round(res_forecast["sri_j90"], 1),
        "sri_j30_lower"       : round(res_forecast["sri_j30_lower"], 1),
        "sri_j90_lower"       : round(res_forecast["sri_j90_lower"], 1),
        "sri_j30_upper"       : round(res_forecast["sri_j30_upper"], 1),
        "sri_j90_upper"       : round(res_forecast["sri_j90_upper"], 1),
        "label_actuel"        : label_actuel,
        "label_j30"           : label_j30,
        "label_j90"           : label_j90,
        "alerte"              : alerte,
        "methode_forecast"    : res_forecast["methode"],
        "nb_pts_historique"   : nb_pts_historique,
        "fiabilite_forecast"  : fiabilite_forecast,
    }


resultats = []
erreurs   = 0
for nom, groupe in df.groupby(COLONNE_FOURNISSEUR):
    try:
        resultats.append(calculer_profil_fournisseur(groupe))
    except Exception as e:
        log.warning("Erreur calcul profil pour '%s' : %s (ignoré)", nom, e)
        erreurs += 1

if erreurs > 0:
    log.warning("%d fournisseurs ignorés pour cause d'erreur", erreurs)

forecast_df = pd.DataFrame(resultats).sort_values("sri_actuel")
log.info("Fournisseurs analysés : %d", len(forecast_df))

methodes = forecast_df["methode_forecast"].value_counts()
for m, n in methodes.items():
    log.info("  Méthode '%s' : %d fournisseurs", m, n)


# ══════════════════════════════════════════════════════════════════
# 4. CLUSTERING DES FOURNISSEURS (ENRICHI)
# ══════════════════════════════════════════════════════════════════
log.info("[3/6] Clustering des fournisseurs...")


def classer_profil(row):
    sri = row["sri_actuel"]
    vm  = row["variation_mensuelle"]
    vm  = 0.0 if pd.isna(vm) else float(vm)
    pct_e = row["pct_eleve"]
    backup = row.get("has_backup", 0)

    if sri >= 70 and vm >= 0:
        return "Stable fiable"
    elif sri >= 55 and vm < -1:
        return "En dégradation"
    elif sri < 45 or pct_e > 20:
        if backup == 0:
            return "Fragile sans backup"   # ← sous-catégorie ajoutée
        return "Fragile"
    else:
        return "À surveiller"


forecast_df["profil_cluster"] = forecast_df.apply(classer_profil, axis=1)
for profil, n in forecast_df["profil_cluster"].value_counts().items():
    log.info("  %-25s : %d fournisseurs", profil, n)


# ══════════════════════════════════════════════════════════════════
# 5. ALERTES
# ══════════════════════════════════════════════════════════════════
log.info("[4/6] Alertes...")

urgent    = forecast_df[forecast_df["alerte"] == "URGENT"]
attention = forecast_df[forecast_df["alerte"] == "ATTENTION"]
ok        = forecast_df[forecast_df["alerte"] == "OK"]

log.info("URGENT    : %d", len(urgent))
log.info("ATTENTION : %d", len(attention))
log.info("OK        : %d", len(ok))

log.info("── Top 10 fournisseurs les plus à risque ──")
for _, row in forecast_df.head(10).iterrows():
    log.info("  [%s] %-30s  SRI=%.1f → J90=%.1f  [%s] Fiab:%d%%",
             row["alerte"], str(row["fournisseur"])[:30],
             row["sri_actuel"], row["sri_j90"],
             row["methode_forecast"], row["fiabilite_forecast"])


# ══════════════════════════════════════════════════════════════════
# 6. ENRICHISSEMENT MATÉRIAUX + SAUVEGARDE
# ══════════════════════════════════════════════════════════════════
log.info("[5/6] Enrichissement matériaux...")

cols_merge = [c for c in [
    "fournisseur", "sri_j30", "sri_j90",
    "sri_j90_lower", "sri_j90_upper",
    "label_j30", "label_j90", "alerte",
    "variation_mensuelle", "fiabilite_forecast",
    "profil_cluster", "methode_forecast", "has_backup",
] if c in forecast_df.columns]

df_enrichi = df.merge(
    forecast_df[cols_merge],
    left_on=COLONNE_FOURNISSEUR,
    right_on="fournisseur",
    how="left",
)

df_enrichi["risque_aggrave_j90"] = (
    (df_enrichi["predicted_label"].isin(["Élevé", "Moyen"])) |
    (df_enrichi.get("label_j90", pd.Series(["Faible"] * len(df_enrichi))) == "Élevé")
).astype(int)

log.info("Matériaux à risque aggravé J+90 : %d", df_enrichi["risque_aggrave_j90"].sum())

log.info("[6/6] Sauvegarde...")
try:
    forecast_df.to_csv(PATHS["forecast_fourn"], index=False, encoding="utf-8-sig")
    df_enrichi.to_csv(PATHS["forecast_mat"],   index=False, encoding="utf-8-sig")
    log.info("Forecast fournisseurs → %s", PATHS["forecast_fourn"])
    log.info("Forecast matériaux   → %s", PATHS["forecast_mat"])
except Exception as e:
    log.error("Erreur sauvegarde : %s", e)
    sys.exit(1)

log.info("=" * 60)
log.info("RÉSUMÉ — Étape 3 v4 terminée")
log.info("=" * 60)
log.info("Méthode dominante : %s",
         "Prophet" if PROPHET_DISPONIBLE and nb_snapshots >= 4 else "Linéaire")
log.info("Snapshots historiques : %d", nb_snapshots)
log.info("URGENT    : %d", len(urgent))
log.info("ATTENTION : %d", len(attention))
log.info("OK        : %d", len(ok))
if nb_snapshots < 4:
    log.info("CONSEIL : Lancez step1 chaque mois. Prophet s'active à 4+ snapshots.")
log.info("=" * 60)
