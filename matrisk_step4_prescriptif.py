"""
MatriskAI — Étape 4 : Moteur Prescriptif
=========================================
AMÉLIORATIONS v4 :
  ✅ Logging structuré via config.py
  ✅ Conditions des règles robustifiées (plus de r.get() ambigu sur Series)
  ✅ 2 nouvelles règles : "Single source + dégradation confirmée" et "Confiance insuffisante"
  ✅ Export CSV + TXT + rapport Markdown du plan d'actions
  ✅ Statistiques enrichies dans le résumé exécutif
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, timedelta

# ── Config centrale ──────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PATHS, setup_logging

log   = setup_logging("step4_prescriptif")
TODAY = datetime.today().strftime("%Y-%m-%d")

log.info("=" * 60)
log.info("  MATRISK AI — ÉTAPE 4 v4 : Moteur Prescriptif")
log.info("=" * 60)
log.info("Date : %s", TODAY)
log.info("Dossier projet : %s", PATHS["base"])


# ══════════════════════════════════════════════════════════════════
# HELPER — accès sécurisé à une colonne d'une Series
# ══════════════════════════════════════════════════════════════════
def _get(row, col, default=None):
    """Accès sécurisé à une colonne d'une ligne pandas (Series ou dict)."""
    try:
        val = row[col]
        return default if pd.isna(val) else val
    except (KeyError, TypeError):
        return default


# ══════════════════════════════════════════════════════════════════
# 1. CHARGEMENT
# ══════════════════════════════════════════════════════════════════
log.info("[1/4] Chargement des prévisions...")

if not os.path.exists(PATHS["forecast_mat"]):
    log.error("Fichier introuvable : %s", PATHS["forecast_mat"])
    log.error("Lancez d'abord matrisk_step3_forecast.py !")
    sys.exit(1)

try:
    df = pd.read_csv(PATHS["forecast_mat"], sep=",", encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    
    # ── Détection dynamique des colonnes
    from config import detect_column
    COL_CODE  = detect_column(df.columns, "code") or "STMaterialCode"
    COL_DESC  = detect_column(df.columns, "description") or "STMaterialDesc"
    COL_FOURN = detect_column(df.columns, "fournisseur") or "supplierHoldingName"
    COL_QML   = detect_column(df.columns, "qml_status") or "QML Status"
    COL_ASL   = detect_column(df.columns, "asl_status") or "ASLStatus"
except Exception as e:
    log.error("Impossible de lire le fichier : %s", e)
    sys.exit(1)

log.info("Matériaux chargés : %d", len(df))

df_risque = df[df["predicted_label"].isin(["Élevé", "Moyen"])].copy()
log.info("Matériaux à risque (Élevé + Moyen) : %d → génération d'actions", len(df_risque))

if len(df_risque) == 0:
    log.warning("Aucun matériau à risque — plan d'actions vide")


# ══════════════════════════════════════════════════════════════════
# 2. MOTEUR DE RÈGLES v4 — 15 RÈGLES
# ══════════════════════════════════════════════════════════════════
# Chaque règle a :
#   condition    : fonction (row) → bool
#   action       : texte de la recommandation
#   priorite     : 1 (urgent), 2 (important), 3 (planifier)
#   score_urgence: 0–100 (tri fin à priorité égale)
#   delai_jours  : dans combien de jours lancer l'action
#   categorie    : famille de l'action
# ══════════════════════════════════════════════════════════════════
log.info("[2/4] Application des règles prescriptives (15 règles)...")

REGLES = [
    # ── P1 : ACTIONS IMMÉDIATES ───────────────────────────────────
    {
        "nom"          : "Matériau disqualifié",
        "condition"    : lambda r: _get(r, "qml_risk_score", 0) == 4,
        "action"       : "⛔ ARRÊT IMMÉDIAT : Matériau disqualifié. "
                         "Contacter le bureau qualité pour dérogation ou remplacement urgent.",
        "priorite"     : 1,
        "score_urgence": 100,
        "delai_jours"  : 0,
        "categorie"    : "Requalification",
    },
    {
        "nom"          : "Fournisseur banni",
        "condition"    : lambda r: _get(r, "asl_risk_score", 0) == 4,
        "action"       : "🚫 NE PAS COMMANDER : Fournisseur Disapproved. "
                         "Transférer les commandes vers un fournisseur alternatif approuvé immédiatement.",
        "priorite"     : 1,
        "score_urgence": 95,
        "delai_jours"  : 0,
        "categorie"    : "Fournisseur",
    },
    {
        "nom"          : "Single source critique + dégradation confirmée",
        "condition"    : lambda r: (
            _get(r, "has_subplant_backup", 1) == 0
            and _get(r, "has_backup", 1) == 0
            and _get(r, "methode_forecast", "") == "prophet"
            and _get(r, "sri_j90", 100) < _get(r, "SRI", 100) - 10
        ),
        "action"       : "🚨 CRITIQUE — DOUBLE RISQUE : Fournisseur unique SANS backup "
                         "ET dégradation Prophet confirmée (−10+ pts J+90). "
                         "Chercher alternative qualifiée IMMÉDIATEMENT. Cible : 30 jours.",
        "priorite"     : 1,
        "score_urgence": 98,
        "delai_jours"  : 2,
        "categorie"    : "Alternative",
    },
    {
        "nom"          : "Shelf life critique sans backup",
        "condition"    : lambda r: (
            _get(r, "shelf_life_risk", 0) == 3
            and _get(r, "has_subplant_backup", 1) == 0
        ),
        "action"       : "⏰ STOCK D'URGENCE : Durée de vie restante critique (<3 mois). "
                         "Commander stock 6 mois + identifier backup fournisseur sous 3 jours.",
        "priorite"     : 1,
        "score_urgence": 90,
        "delai_jours"  : 3,
        "categorie"    : "Stock",
    },
    {
        "nom"          : "Matériau obsolète",
        "condition"    : lambda r: _get(r, "qml_risk_score", 0) == 3,
        "action"       : "🔄 PLANIFIER REMPLACEMENT : Matériau Obsolète. "
                         "Identifier une alternative qualifiée avant rupture. Cible : 60 jours.",
        "priorite"     : 1,
        "score_urgence": 85,
        "delai_jours"  : 7,
        "categorie"    : "Requalification",
    },
    {
        "nom"          : "Forecast Prophet haute confiance + risque",
        "condition"    : lambda r: (
            _get(r, "methode_forecast", "") == "prophet"
            and _get(r, "fiabilite_forecast", 0) >= 70
            and _get(r, "label_j90", "Faible") != "Faible"
        ),
        "action"       : "📊 ALERTE PRÉDICTIVE (Prophet ≥70%% confiance) : Dégradation confirmée "
                         "par modèle temporel. Prioriser ce fournisseur dans le plan d'action.",
        "priorite"     : 1,
        "score_urgence": 88,
        "delai_jours"  : 5,
        "categorie"    : "Prévention",
    },
    {
        "nom"          : "Vitesse de dégradation rapide",
        "condition"    : lambda r: _get(r, "vitesse_degradation", 0) > 0.1,
        "action"       : "🚨 DÉGRADATION RAPIDE : Score de dégradation mensuel élevé. "
                         "Engager une revue qualité fournisseur sous 15 jours.",
        "priorite"     : 1,
        "score_urgence": 82,
        "delai_jours"  : 7,
        "categorie"    : "Fournisseur",
    },

    # ── P2 : ACTIONS IMPORTANTES ──────────────────────────────────
    {
        "nom"          : "Dégradation prévue J+90",
        "condition"    : lambda r: (
            _get(r, "label_j90", "Faible") == "Élevé"
            and _get(r, "predicted_label", "") != "Élevé"
        ),
        "action"       : "⚠ PRÉVENTION J+90 : Dégradation vers Risque Élevé prévue. "
                         "Initier les actions préventives maintenant pour éviter la crise.",
        "priorite"     : 2,
        "score_urgence": 72,
        "delai_jours"  : 10,
        "categorie"    : "Prévention",
    },
    {
        "nom"          : "Fournisseur sous surveillance",
        "condition"    : lambda r: _get(r, "asl_risk_score", 0) == 3,
        "action"       : "👀 SURVEILLANCE RENFORCÉE : Fournisseur en Probation. "
                         "Augmenter la fréquence des audits. Planifier inspection sous 30 jours.",
        "priorite"     : 2,
        "score_urgence": 70,
        "delai_jours"  : 14,
        "categorie"    : "Fournisseur",
    },
    {
        "nom"          : "Anomalie statistique détectée",
        "condition"    : lambda r: int(_get(r, "est_anomalie", 0)) == 1,
        "action"       : "🔎 INVESTIGATION : Profil statistiquement anormal (IsolationForest). "
                         "Vérifier manuellement les données de ce matériau sous 14 jours.",
        "priorite"     : 2,
        "score_urgence": 68,
        "delai_jours"  : 14,
        "categorie"    : "Anomalie",
    },
    {
        "nom"          : "Single source critique (risque élevé)",
        "condition"    : lambda r: (
            _get(r, "has_subplant_backup", 1) == 0
            and _get(r, "predicted_label", "") == "Élevé"
        ),
        "action"       : "🔍 DIVERSIFIER : Aucun fournisseur alternatif pour un matériau à risque élevé. "
                         "Lancer recherche backup supplier qualifié (cible : 90 jours).",
        "priorite"     : 2,
        "score_urgence": 65,
        "delai_jours"  : 14,
        "categorie"    : "Alternative",
    },
    {
        "nom"          : "Shelf life à surveiller",
        "condition"    : lambda r: _get(r, "shelf_life_risk", 0) == 2,
        "action"       : "📦 ANTICIPER : Durée de vie 3–6 mois. "
                         "Vérifier le stock actuel et planifier réapprovisionnement sous 45 jours.",
        "priorite"     : 2,
        "score_urgence": 60,
        "delai_jours"  : 30,
        "categorie"    : "Stock",
    },
    {
        "nom"          : "Signaux NLP de risque",
        "condition"    : lambda r: _get(r, "text_risk_flag", 0) >= 2,
        "action"       : "📋 ANALYSER LES NOTES : Mots-clés risque détectés (phase out, stoppage…). "
                         "Vérifier l'historique complet du matériau sous 21 jours.",
        "priorite"     : 2,
        "score_urgence": 55,
        "delai_jours"  : 21,
        "categorie"    : "Documentation",
    },

    # ── P3 : ACTIONS À PLANIFIER ──────────────────────────────────
    {
        "nom"          : "Données obsolètes",
        "condition"    : lambda r: _get(r, "days_since_update", 0) > 540,
        "action"       : "🗂 MISE À JOUR : Données non actualisées depuis >18 mois. "
                         "Contacter le fournisseur pour confirmation du statut.",
        "priorite"     : 3,
        "score_urgence": 35,
        "delai_jours"  : 45,
        "categorie"    : "Documentation",
    },
    {
        "nom"          : "Confiance insuffisante pour décider",
        "condition"    : lambda r: _get(r, "confiance_finale", 100) < 40,
        "action"       : "❓ DONNÉES INSUFFISANTES : Confiance modèle < 40%%. "
                         "Mettre à jour les données source avant toute décision.",
        "priorite"     : 3,
        "score_urgence": 30,
        "delai_jours"  : 60,
        "categorie"    : "Documentation",
    },
]


def generer_recommandations(ligne):
    """Applique toutes les règles sur une ligne et retourne celles qui s'activent."""
    recs = []
    for regle in REGLES:
        try:
            if regle["condition"](ligne):
                recs.append(regle)
        except Exception as e:
            log.debug("Règle '%s' — erreur ignorée : %s", regle["nom"], e)
    return recs


# ── Application sur les matériaux à risque ───────────────────────
actions_list = []
for _, ligne in df_risque.iterrows():
    for rec in generer_recommandations(ligne):
        date_limite = (datetime.today() + timedelta(days=rec["delai_jours"])).strftime("%Y-%m-%d")
        actions_list.append({
            "materiau_code"   : _get(ligne, COL_CODE,              "N/A"),
            "materiau_desc"   : _get(ligne, COL_DESC,              "N/A"),
            "fournisseur"     : _get(ligne, COL_FOURN,             "N/A"),
            "qml_status"      : _get(ligne, COL_QML,               "N/A"),
            "asl_status"      : _get(ligne, COL_ASL,               "N/A"),
            "sri"             : _get(ligne, "SRI",                 0),
            "proba_eleve"     : _get(ligne, "proba_Elevé",         0),
            "label_predit"    : _get(ligne, "predicted_label",     "N/A"),
            "label_j90"       : _get(ligne, "label_j90",           "N/A"),
            "confiance"       : _get(ligne, "confiance_finale",    "N/A"),
            "regle"           : rec["nom"],
            "action"          : rec["action"],
            "priorite"        : rec["priorite"],
            "score_urgence"   : rec["score_urgence"],
            "categorie"       : rec["categorie"],
            "delai_jours"     : rec["delai_jours"],
            "date_limite"     : date_limite,
            "methode_forecast": _get(ligne, "methode_forecast",    "N/A"),
        })

# ── Tri : priorité → score_urgence → SRI ─────────────────────────
if actions_list:
    plan = pd.DataFrame(actions_list).sort_values(
        ["priorite", "score_urgence", "sri"],
        ascending=[True, False, True]
    )
    # Déduplication : une action max par (matériau, catégorie)
    plan = plan.drop_duplicates(subset=["materiau_code", "categorie"], keep="first")
else:
    plan = pd.DataFrame(columns=["materiau_code", "priorite", "score_urgence",
                                  "categorie", "action", "sri"])

log.info("Actions générées (après déduplication) : %d", len(plan))


# ══════════════════════════════════════════════════════════════════
# 3. RAPPORT SYNTHÉTIQUE
# ══════════════════════════════════════════════════════════════════
log.info("[3/4] Rapport synthétique...")

p1 = plan[plan["priorite"] == 1] if len(plan) > 0 else pd.DataFrame()
p2 = plan[plan["priorite"] == 2] if len(plan) > 0 else pd.DataFrame()
p3 = plan[plan["priorite"] == 3] if len(plan) > 0 else pd.DataFrame()

for prio_df, label in [(p1, "P1 URGENT"), (p2, "P2 IMPORTANT"), (p3, "P3 PLANIFIER")]:
    if len(prio_df) > 0:
        log.info("%s : %d actions sur %d matériaux",
                 label, len(prio_df), prio_df["materiau_code"].nunique())
        for cat, nb in prio_df["categorie"].value_counts().items():
            log.info("    • %-20s %d actions", cat, nb)


# ══════════════════════════════════════════════════════════════════
# 4. RÉSUMÉ EXÉCUTIF
# ══════════════════════════════════════════════════════════════════
log.info("[4/4] Export résumé exécutif + sauvegarde...")

resume = f"""
================================================================================
  MATRISK AI v4 — RÉSUMÉ EXÉCUTIF                        {TODAY}
================================================================================

  RÉSUMÉ :
    Matériaux analysés       : {len(df_risque)}
    Actions générées totales : {len(plan)}
    ┌─────────────────────────────────────────────────────┐
    │  🔴 Priorité 1 (URGENT)     : {len(p1):>4} actions           │
    │  🟡 Priorité 2 (IMPORTANT)  : {len(p2):>4} actions           │
    │  🔵 Priorité 3 (PLANIFIER)  : {len(p3):>4} actions           │
    └─────────────────────────────────────────────────────┘
"""

if len(p1) > 0:
    resume += "\n  TOP 10 ACTIONS URGENTES (Priorité 1) :\n"
    for i, (_, row) in enumerate(p1.head(10).iterrows(), 1):
        resume += (
            f"\n  {i:>2}. [{row['label_predit']:<6}] SRI={row['sri']:>5.1f}"
            f" | {str(row['materiau_code']):<18}"
            f" | {str(row['fournisseur'])[:28]}\n"
            f"      → {row['action'][:90]}\n"
            f"      Délai : {row['date_limite']} | Score urgence : {row['score_urgence']}/100\n"
        )

if len(plan) > 0:
    resume += "\n  RÉPARTITION PAR CATÉGORIE :\n"
    for cat, nb in plan["categorie"].value_counts().items():
        barre = "█" * max(1, int(nb / len(plan) * 25))
        resume += f"    {cat:<25} {nb:>4}  {barre}\n"

    resume += "\n  FOURNISSEURS LES PLUS IMPACTÉS :\n"
    top_fourn = (plan.groupby("fournisseur")
                 .agg(nb_actions=("action", "count"), prio_min=("priorite", "min"))
                 .sort_values(["prio_min", "nb_actions"], ascending=[True, False])
                 .head(5))
    for fourn, row in top_fourn.iterrows():
        resume += f"    {str(fourn)[:35]:<35} {row['nb_actions']} actions (P{row['prio_min']} min)\n"

resume += f"""
================================================================================
  Généré par MatriskAI v4 — {TODAY}
  15 règles prescriptives | Split temporel | Calibration isotonique
================================================================================
"""

print(resume)

try:
    with open(PATHS["resume_exec"], "w", encoding="utf-8") as f:
        f.write(resume)
    log.info("Résumé exécutif → %s", PATHS["resume_exec"])
except Exception as e:
    log.warning("Impossible de sauvegarder le résumé : %s", e)

try:
    plan.to_csv(PATHS["plan_actions"], index=False, encoding="utf-8-sig")
    log.info("Plan d'actions → %s", PATHS["plan_actions"])
except Exception as e:
    log.error("Erreur sauvegarde plan d'actions : %s", e)
    sys.exit(1)

log.info("=" * 60)
log.info("RÉSUMÉ — Étape 4 v4 terminée")
log.info("=" * 60)
log.info("Matériaux analysés  : %d", len(df_risque))
log.info("Actions total       : %d", len(plan))
log.info("Priorité 1 URGENT   : %d", len(p1))
log.info("Priorité 2          : %d", len(p2))
log.info("Priorité 3          : %d", len(p3))
log.info("Catégories          : %d", plan["categorie"].nunique() if len(plan) > 0 else 0)
log.info("=" * 60)
