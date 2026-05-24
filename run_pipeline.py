"""
MatriskAI — Lanceur de pipeline complet
=========================================
Lance les étapes dans l'ordre avec gestion d'erreurs et timing.

USAGE :
  python run_pipeline.py                        # toutes les étapes (1→4)
  python run_pipeline.py --steps 134            # étapes 1, 3 et 4 seulement
  python run_pipeline.py --fichier mon.xlsx     # avec fichier Excel custom
  python run_pipeline.py --steps 34 --no-train  # forcer skip step 2
"""

import subprocess
import sys
import os
import argparse
import time
from datetime import datetime

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


# ── Chemins des scripts ───────────────────────────────────────────
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
STEPS = {
    1: os.path.join(SCRIPTS_DIR, "matrisk_step1_cleaning.py"),
    2: os.path.join(SCRIPTS_DIR, "matrisk_step2_train.py"),
    3: os.path.join(SCRIPTS_DIR, "matrisk_step3_forecast.py"),
    4: os.path.join(SCRIPTS_DIR, "matrisk_step4_prescriptif.py"),
}

STEP_LABELS = {
    1: "Nettoyage & Feature Engineering",
    2: "XGBoost + Calibration + SHAP",
    3: "Forecast Prophet / Linéaire",
    4: "Moteur Prescriptif",
}


def print_banner():
    print("\n" + "=" * 65)
    print("  ◈  MATRISK AI — Pipeline Runner v4")
    print("=" * 65)
    print(f"  Lancé le : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Python   : {sys.executable}")
    print("=" * 65)


def run_step(step_num: int, script_path: str, extra_args: str = "") -> bool:
    """Lance un step et retourne True si succès, False si échec."""
    label = STEP_LABELS.get(step_num, f"Step {step_num}")
    print(f"\n{'─' * 65}")
    print(f"  ▶  Step {step_num} — {label}")
    print(f"{'─' * 65}")

    if not os.path.exists(script_path):
        print(f"  ❌ Script introuvable : {script_path}")
        return False

    cmd = f'"{sys.executable}" "{script_path}" {extra_args}'.strip()
    t0 = time.time()

    try:
        result = subprocess.run(cmd, shell=True, check=False)
        elapsed = time.time() - t0

        if result.returncode == 0:
            print(f"\n  ✅ Step {step_num} terminé en {elapsed:.1f}s")
            return True
        else:
            print(f"\n  ❌ Step {step_num} a échoué (code {result.returncode}) après {elapsed:.1f}s")
            return False

    except KeyboardInterrupt:
        print(f"\n  ⚠  Step {step_num} interrompu par l'utilisateur")
        return False
    except Exception as e:
        print(f"\n  ❌ Erreur inattendue Step {step_num} : {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="MatriskAI — Lance le pipeline de A à Z"
    )
    parser.add_argument(
        "--steps", default="1234",
        help="Étapes à lancer (ex: '1234', '134', '4'). Défaut: toutes"
    )
    parser.add_argument(
        "--fichier", default=None,
        help="Chemin vers un fichier Excel custom (transmis à step 1)"
    )
    parser.add_argument(
        "--stop-on-error", action="store_true",
        help="Arrêter le pipeline si une étape échoue (défaut: continuer)"
    )
    args = parser.parse_args()

    print_banner()

    # Déterminer les étapes à lancer
    steps_to_run = []
    for char in args.steps:
        if char.isdigit():
            n = int(char)
            if n in STEPS:
                steps_to_run.append(n)
            else:
                print(f"  ⚠ Step {n} inconnu — ignoré")

    if not steps_to_run:
        print("  ❌ Aucune étape valide spécifiée.")
        sys.exit(1)

    print(f"\n  Étapes planifiées : {' → '.join(str(s) for s in steps_to_run)}")
    if args.fichier:
        print(f"  Fichier custom    : {args.fichier}")

    # Lancer les étapes
    t_start  = time.time()
    resultats = {}

    for step_num in steps_to_run:
        extra = f"--fichier \"{args.fichier}\"" if (args.fichier and step_num == 1) else ""
        ok = run_step(step_num, STEPS[step_num], extra)
        resultats[step_num] = ok

        if not ok and args.stop_on_error:
            print(f"\n  🛑 Arrêt du pipeline (--stop-on-error) après échec Step {step_num}")
            break

    # Résumé final
    t_total = time.time() - t_start
    print(f"\n{'=' * 65}")
    print(f"  RÉSUMÉ — Pipeline terminé en {t_total:.1f}s")
    print(f"{'=' * 65}")
    for step_num, ok in resultats.items():
        status = "✅" if ok else "❌"
        print(f"  {status}  Step {step_num} — {STEP_LABELS[step_num]}")

    n_ok  = sum(1 for ok in resultats.values() if ok)
    n_err = sum(1 for ok in resultats.values() if not ok)
    print(f"\n  {n_ok}/{len(resultats)} étapes réussies")

    if n_err == 0:
        print("\n  ✅ Pipeline complet — Lancez le dashboard :")
        print("     streamlit run matrisk_step5_dashboard.py")
    else:
        print(f"\n  ⚠  {n_err} étape(s) en erreur — consultez les logs dans Logs/")

    print("=" * 65)
    sys.exit(0 if n_err == 0 else 1)


if __name__ == "__main__":
    main()
