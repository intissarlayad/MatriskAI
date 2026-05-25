"""
MatriskAI — Étape 1 : Nettoyage & Feature Engineering
======================================================
AMÉLIORATIONS v4 :
  ✅ Logging structuré (fichier + console) via config.py
  ✅ Config centralisée (chemins, encodages, colonnes)
  ✅ vitesse_degradation calculée sur VRAI delta historique (plus simulée)
  ✅ date_inconnue : flag binaire explicite (plus de -1 magique)
  ✅ days_since_update : fillna sur médiane (plus de -1)
  ✅ score_confiance : logique corrigée (pas de double pénalité)
  ✅ Validation des colonnes obligatoires avec rapport d'erreur clair
  ✅ Argument --fichier pour fichier Excel custom

ENTRÉE  : QML report by Plant.xlsx  (ou --fichier custom)
SORTIE  : dataset_clean.csv
          historique_sri.csv
"""

import pandas as pd
import numpy as np
import re
import os
import sys
import argparse
from datetime import datetime

# ── Config centrale ──────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PATHS, QML_MAP, ASL_MAP, SRI_THRESHOLDS, detect_column, setup_logging

log   = setup_logging("step1_cleaning")
TODAY = datetime.today().strftime("%Y-%m-%d")

# ── Argument CLI ─────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="MatriskAI — Step 1")
parser.add_argument("--fichier", default=None, help="Chemin vers l'Excel custom")
args, _ = parser.parse_known_args()

INPUT_FILE = args.fichier if args.fichier else PATHS["input_excel"]

log.info("=" * 60)
log.info("  MATRISK AI — ÉTAPE 1 v4 : Feature Engineering + Historique")
log.info("=" * 60)
log.info("Date du snapshot : %s", TODAY)
log.info("Dossier projet   : %s", PATHS["base"])
log.info("Fichier source   : %s", INPUT_FILE)

os.makedirs(PATHS["snapshots_dir"], exist_ok=True)


# ══════════════════════════════════════════════════════════════════
# 1. CHARGEMENT & VALIDATION
# ══════════════════════════════════════════════════════════════════
log.info("[1/9] Chargement du fichier Excel...")

if not os.path.exists(INPUT_FILE):
    log.error("Fichier introuvable : %s", INPUT_FILE)
    log.error("Vérifiez le chemin ou utilisez --fichier /chemin/vers/excel.xlsx")
    sys.exit(1)

try:
    df = pd.read_excel(INPUT_FILE, sheet_name=0)
except Exception as e:
    log.error("Impossible de lire le fichier Excel : %s", e)
    sys.exit(1)

df.columns = [c.strip() for c in df.columns]
log.info("Chargé : %d lignes | %d colonnes", df.shape[0], df.shape[1])

# ── Validation colonnes obligatoires ─────────────────────────────
COLS_OBLIGATOIRES = ["qml_status", "asl_status"]
erreurs_col = []
for key in COLS_OBLIGATOIRES:
    col = detect_column(df.columns, key)
    if col is None:
        erreurs_col.append(key)

if erreurs_col:
    log.error("Colonnes obligatoires manquantes : %s", erreurs_col)
    log.error("Colonnes disponibles : %s", list(df.columns))
    sys.exit(1)

# ── Détection colonnes optionnelles ──────────────────────────────
COL_QML    = detect_column(df.columns, "qml_status")
COL_ASL    = detect_column(df.columns, "asl_status")
COL_NLP    = detect_column(df.columns, "nlp")
COL_SHELF  = detect_column(df.columns, "shelf_life")
COL_DATE   = detect_column(df.columns, "updated")
COL_CODE   = detect_column(df.columns, "code")
COL_FOURN  = detect_column(df.columns, "fournisseur")
COL_BACKUP = detect_column(df.columns, "fournisseur")  # réutilisé pour SuppSubPlant

# Backup fournisseur alternatif (colonne spécifique)
COL_BACKUP = "SuppSubPlant1Name" if "SuppSubPlant1Name" in df.columns else None

log.info("Colonnes détectées :")
log.info("  QML      : %s", COL_QML)
log.info("  ASL      : %s", COL_ASL)
log.info("  NLP      : %s", COL_NLP or '(non trouvée — text_risk_flag=0)')
log.info("  Shelf    : %s", COL_SHELF or '(non trouvée — shelf_life_risk=3)')
log.info("  Date MAJ : %s", COL_DATE or '(non trouvée — date_inconnue=1)')
log.info("  Code mat : %s", COL_CODE or '(non trouvée — historique désactivé)')
log.info("  Fourn.   : %s", COL_FOURN or '(non trouvée)')


# ══════════════════════════════════════════════════════════════════
# 2. ENCODAGE QML
# ══════════════════════════════════════════════════════════════════
log.info("[2/9] Encodage QML Status...")
df["qml_risk_score"] = df[COL_QML].map(QML_MAP).fillna(2)

for statut, score in QML_MAP.items():
    nb = (df[COL_QML] == statut).sum()
    if nb > 0:
        log.info("  %-24s → %d  (%5d | %.1f%%)", statut, score, nb, nb / len(df) * 100)

# Statuts inconnus
inconnus_qml = df[~df[COL_QML].isin(QML_MAP)][COL_QML].dropna().unique()
if len(inconnus_qml) > 0:
    log.warning("Statuts QML inconnus → encodés à 2 : %s", list(inconnus_qml))


# ══════════════════════════════════════════════════════════════════
# 3. ENCODAGE ASL
# ══════════════════════════════════════════════════════════════════
log.info("[3/9] Encodage ASL Status...")
df["asl_risk_score"] = df[COL_ASL].map(ASL_MAP).fillna(2)

inconnus_asl = df[~df[COL_ASL].isin(ASL_MAP)][COL_ASL].dropna().unique()
if len(inconnus_asl) > 0:
    log.warning("Statuts ASL inconnus → encodés à 2 : %s", list(inconnus_asl))


# ══════════════════════════════════════════════════════════════════
# 4. SCORE COMBINÉ
# ══════════════════════════════════════════════════════════════════
log.info("[4/9] Score combiné QML (60%%) + ASL (40%%)...")
df["combined_risk_score"] = (
    df["qml_risk_score"] * 0.6 + df["asl_risk_score"] * 0.4
).round(2)
log.info("  combined_risk_score — moy: %.2f | max: %.2f",
         df["combined_risk_score"].mean(), df["combined_risk_score"].max())


# ══════════════════════════════════════════════════════════════════
# 5. FEATURES TEMPORELLES (CORRIGÉES)
# ══════════════════════════════════════════════════════════════════
log.info("[5/9] Features temporelles...")
ref_date = pd.Timestamp(TODAY)

# ── date_inconnue : flag binaire explicite (BUG FIX #2) ──────────
if COL_DATE:
    df["updated_dt"]    = pd.to_datetime(df[COL_DATE], errors="coerce")
    df["date_inconnue"] = df["updated_dt"].isna().astype(int)
    # Remplir les NaT par la médiane des dates connues
    mediane_jours = (ref_date - df["updated_dt"]).dt.days.median()
    mediane_jours = mediane_jours if not np.isnan(mediane_jours) else 365
    df["days_since_update"] = (ref_date - df["updated_dt"]).dt.days.fillna(mediane_jours).astype(int)
else:
    df["date_inconnue"]   = 1
    df["days_since_update"] = 365  # valeur neutre
    log.warning("Colonne date non trouvée — days_since_update=365, date_inconnue=1")

log.info("  days_since_update — moy: %.0f jours | dates inconnues: %d",
         df[df["date_inconnue"] == 0]["days_since_update"].mean(),
         df["date_inconnue"].sum())

# ── vitesse_degradation : calculée sur l'HISTORIQUE RÉEL (BUG FIX #1) ──
log.info("  Calcul vitesse_degradation...")
HISTORIQUE_CSV = PATHS["historique"]

if os.path.exists(HISTORIQUE_CSV) and COL_CODE:
    try:
        hist = pd.read_csv(HISTORIQUE_CSV, encoding="utf-8-sig")
        hist["date"] = pd.to_datetime(hist["date"])
        # Snapshot précédent = dernier snapshot avant aujourd'hui
        hist_avant = hist[hist["date"].dt.strftime("%Y-%m-%d") < TODAY]
        if not hist_avant.empty:
            snap_prec = (
                hist_avant
                .sort_values("date")
                .groupby("materiau_code")
                .last()
                .reset_index()[["materiau_code", "SRI", "date"]]
            )
            # SRI pas encore calculé ici → on fait un SRI préliminaire pour le delta
            sri_prelim = (
                100
                - (df["combined_risk_score"] / 4 * 40)
            ).clip(0, 100)
            snap_prec = snap_prec.rename(columns={"materiau_code": COL_CODE, "SRI": "SRI_prev", "date": "date_prev"})
            df = df.merge(snap_prec, on=COL_CODE, how="left")
            df["delta_jours"] = (ref_date - pd.to_datetime(df["date_prev"])).dt.days.fillna(30)
            df["delta_jours"] = df["delta_jours"].replace(0, 30)
            # vitesse = pts SRI perdus par mois (positif = dégradation)
            df["vitesse_degradation"] = (
                (df["SRI_prev"].fillna(sri_prelim) - sri_prelim) / (df["delta_jours"] / 30)
            ).round(4).fillna(0.0).clip(-5.0, 5.0)
            df.drop(columns=["SRI_prev", "date_prev", "delta_jours"], inplace=True)
            log.info("  vitesse_degradation calculée sur historique réel (cappée entre -5.0 et +5.0)")
        else:
            df["vitesse_degradation"] = 0.0
            log.info("  Pas de snapshot précédent — vitesse_degradation=0.0 (premier run)")
    except Exception as e:
        log.warning("Erreur lecture historique pour vitesse_degradation : %s", e)
        df["vitesse_degradation"] = 0.0
else:
    # Fallback : approximation si pas d'historique du tout
    vitesse_approx = np.where(
        (df["days_since_update"] > 0) & (df["date_inconnue"] == 0),
        (df["combined_risk_score"] / (df["days_since_update"] / 30 + 1)).round(4),
        0.0
    )
    df["vitesse_degradation"] = np.clip(vitesse_approx, -5.0, 5.0)
    log.info("  vitesse_degradation approximée (pas d'historique disponible)")

log.info("  vitesse_degradation — moy: %.4f | max: %.4f",
         df["vitesse_degradation"].mean(), df["vitesse_degradation"].max())


# ══════════════════════════════════════════════════════════════════
# 6. SHELF LIFE
# ══════════════════════════════════════════════════════════════════
log.info("[6/9] Shelf life...")

def convertir_shelf_life(v):
    if pd.isna(v): return 3   # inconnu = risque max par défaut
    if v < 3:     return 3   # critique
    if v < 6:     return 2   # à surveiller
    if v < 12:    return 1   # attention
    return 0                  # OK

if COL_SHELF:
    df["shelf_life_risk"] = df[COL_SHELF].apply(convertir_shelf_life)
else:
    df["shelf_life_risk"] = 3
    log.warning("Colonne shelf life non trouvée — shelf_life_risk=3 (risque max)")

dist_sl = df["shelf_life_risk"].value_counts().sort_index()
for k, v in dist_sl.items():
    label = {0: "OK (>12m)", 1: "<12 mois", 2: "<6 mois", 3: "<3m/inconnu"}[k]
    log.info("  shelf_life_risk=%d (%s) : %d matériaux", k, label, v)


# ══════════════════════════════════════════════════════════════════
# 7. FEATURES BINAIRES
# ══════════════════════════════════════════════════════════════════
log.info("[7/9] Features binaires...")

# E-certificate
cert_cols = [c for c in df.columns if "cert" in c.lower() or "certificate" in c.lower()]
if cert_cols:
    df["has_ecertificate"] = df[cert_cols[0]].notna().astype(int)
    log.info("  has_ecertificate depuis '%s' : %d présents", cert_cols[0], df["has_ecertificate"].sum())
else:
    df["has_ecertificate"] = 0
    log.warning("Aucune colonne certificat trouvée — has_ecertificate=0")

# Backup fournisseur
if COL_BACKUP and COL_BACKUP in df.columns:
    df["has_subplant_backup"] = df[COL_BACKUP].notna().astype(int)
    log.info("  has_subplant_backup depuis '%s' : %d ont un backup", COL_BACKUP, df["has_subplant_backup"].sum())
else:
    df["has_subplant_backup"] = 0
    log.warning("Colonne backup fournisseur non trouvée — has_subplant_backup=0")


# ══════════════════════════════════════════════════════════════════
# 7b. NLP — Analyse des notes textuelles
# ══════════════════════════════════════════════════════════════════
log.info("  NLP — Analyse des mots-clés de risque...")

LEMME_DICT = {
    "cancel": "cancel", "cancelled": "cancel", "cancelling": "cancel",
    "disqualify": "disqualify", "disqualified": "disqualify",
    "phase": "phase", "phased": "phase", "phasing": "phase",
    "obsolete": "obsolete", "obsoleted": "obsolete",
    "stop": "stop", "stopped": "stop", "stoppage": "stop",
    "downgrade": "downgrade", "downgraded": "downgrade",
    "discontinue": "discontinue", "discontinued": "discontinue",
    "end of life": "discontinue", "eol": "discontinue",
}
LEMMES_RISQUE  = {"cancel", "disqualify", "phase", "obsolete", "stop", "downgrade", "discontinue"}
BIGRAMS_RISQUE = [
    "phase out", "no receiving", "no usage", "supplier phase out",
    "project cancel", "end of life", "eol", "not recommended",
    "do not use", "last time buy",
]

def analyser_risque_nlp(texte):
    if pd.isna(texte) or str(texte).strip() == "":
        return 0
    t = str(texte).lower()
    score = sum(1 for b in BIGRAMS_RISQUE if b in t)
    tokens = re.findall(r"[a-z][a-z\-]*", t)
    score += sum(1 for tk in tokens if LEMME_DICT.get(tk, tk) in LEMMES_RISQUE)
    return score

if COL_NLP:
    df["text_risk_flag"] = df[COL_NLP].apply(analyser_risque_nlp)
    n_nlp_risque = (df["text_risk_flag"] > 0).sum()
    log.info("  text_risk_flag — matériaux avec signaux NLP : %d (%.1f%%)",
             n_nlp_risque, n_nlp_risque / len(df) * 100)
else:
    df["text_risk_flag"] = 0
    log.warning("Colonne NLP non trouvée — text_risk_flag=0")


# ══════════════════════════════════════════════════════════════════
# 8. SRI + LABEL + SCORE DE CONFIANCE (CORRIGÉ)
# ══════════════════════════════════════════════════════════════════
log.info("[8/9] SRI, label, score de confiance...")

df["SRI"] = (
    100
    - (df["combined_risk_score"] / 4 * 40)
    - (df["shelf_life_risk"]           / 3 * 25)
    - (df["text_risk_flag"].clip(0, 3) / 3 * 20)
    + (df["has_ecertificate"]    * 10)
    + (df["has_subplant_backup"] * 5)
).round(1).clip(0, 100)

# Assertion de sécurité
assert df["SRI"].between(0, 100).all(), "SRI hors bornes [0, 100] — vérifier la formule"

def assigner_label(s):
    if s >= SRI_THRESHOLDS["Faible"]: return "Faible"
    if s >= SRI_THRESHOLDS["Moyen"]:  return "Moyen"
    return "Élevé"

df["risk_label"] = df["SRI"].apply(assigner_label)

# ── Score de confiance CORRIGÉ (BUG FIX #3) ──────────────────────
# Logique claire : pénalités mutuellement exclusives pour les dates
def calculer_confiance(row):
    conf = 100
    dsu = row["days_since_update"]
    date_inc = row["date_inconnue"]

    if date_inc == 1:
        conf -= 20                  # date inconnue → pénalité unique (pas de double pénalité)
    elif dsu > 540:
        conf -= 25                  # données > 18 mois
    elif dsu > 270:
        conf -= 10                  # données > 9 mois

    if row["shelf_life_risk"] == 3:
        conf -= 10                  # shelf life inconnu ou critique
    if row["has_ecertificate"] == 0:
        conf -= 5                   # pas de certificat

    return max(conf, 10)

df["score_confiance"] = df.apply(calculer_confiance, axis=1)

log.info("Distribution des labels :")
for label, nb in df["risk_label"].value_counts().items():
    log.info("  %-10s %5d (%.1f%%)", label, nb, nb / len(df) * 100)
log.info("SRI          — moy: %.1f | min: %.1f | max: %.1f",
         df["SRI"].mean(), df["SRI"].min(), df["SRI"].max())
log.info("Confiance    — moy: %.1f/100", df["score_confiance"].mean())


# ══════════════════════════════════════════════════════════════════
# 9. HISTORIQUE TEMPOREL
# ══════════════════════════════════════════════════════════════════
log.info("[9/9] Mise à jour de l'historique temporel...")

if COL_CODE and COL_CODE in df.columns:
    snapshot = pd.DataFrame({
        "date"            : TODAY,
        "materiau_code"   : df[COL_CODE].astype(str),
        "fournisseur"     : df[COL_FOURN].astype(str) if COL_FOURN else "N/A",
        "SRI"             : df["SRI"],
        "qml_risk_score"  : df["qml_risk_score"],
        "asl_risk_score"  : df["asl_risk_score"],
        "combined_risk"   : df["combined_risk_score"],
        "risk_label"      : df["risk_label"],
        "score_confiance" : df["score_confiance"],
        "est_anomalie"    : 0,  # sera mis à jour par step2 si relancé
    })

    if os.path.exists(HISTORIQUE_CSV):
        try:
            hist_existant = pd.read_csv(HISTORIQUE_CSV, encoding="utf-8-sig")
            hist_existant = hist_existant[hist_existant["date"] != TODAY]
            historique    = pd.concat([hist_existant, snapshot], ignore_index=True)
            historique    = historique.drop_duplicates(subset=["date", "materiau_code"], keep="last")
        except Exception as e:
            log.warning("Erreur lecture historique existant : %s — remplacement", e)
            historique = snapshot
    else:
        historique = snapshot

    nb_snapshots = historique["date"].nunique()
    historique.to_csv(HISTORIQUE_CSV, index=False, encoding="utf-8-sig")

    snapshot_path = os.path.join(PATHS["snapshots_dir"], f"snapshot_{TODAY}.csv")
    snapshot.to_csv(snapshot_path, index=False, encoding="utf-8-sig")

    log.info("Historique mis à jour : %d snapshot(s)", nb_snapshots)
    log.info("Fichier historique    : %s", HISTORIQUE_CSV)
    log.info("Snapshot daté         : %s", snapshot_path)

    if nb_snapshots < 4:
        log.info("CONSEIL : Lancez step1 mensuellement. Prophet s'active à 4+ snapshots.")
else:
    log.warning("Colonne code matériau introuvable — historique non créé")


# ══════════════════════════════════════════════════════════════════
# SAUVEGARDE DATASET PRINCIPAL
# ══════════════════════════════════════════════════════════════════
try:
    df.to_csv(PATHS["dataset_clean"], index=False, encoding="utf-8-sig")
    log.info("Dataset sauvegardé → %s", PATHS["dataset_clean"])
except Exception as e:
    log.error("Impossible de sauvegarder le dataset : %s", e)
    sys.exit(1)

FEATURES_FINALES = [
    "qml_risk_score", "asl_risk_score", "combined_risk_score",
    "days_since_update", "date_inconnue", "vitesse_degradation",
    "shelf_life_risk", "has_ecertificate", "has_subplant_backup",
    "text_risk_flag", "score_confiance", "SRI", "risk_label",
]

log.info("=" * 60)
log.info("RÉSUMÉ — Étape 1 v4 terminée")
log.info("=" * 60)
log.info("Dataset sauvegardé  → %s", PATHS["dataset_clean"])
log.info("Historique temporel → %s", HISTORIQUE_CSV)
log.info("Features créées (%d) :", len(FEATURES_FINALES))
for f in FEATURES_FINALES:
    if f in df.columns:
        log.info("  %-30s ex: %s", f, df[f].iloc[0])
log.info("=" * 60)
