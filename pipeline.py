"""
pipeline.py — Orchestrateur ELT GitHub Analytics
Extract → Load(raw) → Transform → Load(staging + intermediate + marts)
"""

import logging
import sys
import os
import importlib
from datetime import datetime
from pathlib import Path

os.makedirs("logs", exist_ok=True)

LOG_FILE = f"logs/pipeline_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PIPELINE] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE),
    ],
)
log = logging.getLogger(__name__)

BANNER = """
╔══════════════════════════════════════════════════════════╗
║      GITHUB ANALYTICS — DATA ANALYSIS PIPELINE          ║
║         ELT : Extract → Load(raw) → Transform           ║
║               → Load(staging + intermediate + marts)    ║
╚══════════════════════════════════════════════════════════╝"""

STEPS = [
    ("STEP 1/3 — EXTRACT",          "elt.extract.extract",    "run"),
    ("STEP 2/3 — TRANSFORM",         "elt.transform.transform","run"),
    ("STEP 3/3 — LOAD (ALL LAYERS)", "elt.load.load",          "run"),
]


def run_pipeline():
    start = datetime.utcnow()
    print(BANNER)
    log.info(f"Démarrage : {start.strftime('%Y-%m-%d %H:%M:%S')} UTC")

    for label, module_path, func in STEPS:
        log.info(f"\n{'─'*58}\n  {label}\n{'─'*58}")
        t0 = datetime.utcnow()
        try:
            mod = importlib.import_module(module_path)
            getattr(mod, func)()
            log.info(f"  ✓ {label} — {(datetime.utcnow()-t0).total_seconds():.1f}s")
        except Exception as e:
            log.error(f"  ✗ ERREUR : {e}", exc_info=True)
            sys.exit(1)

    total = (datetime.utcnow() - start).total_seconds()
    log.info(f"""
╔══════════════════════════════════════════════════════════╗
║  PIPELINE TERMINÉ EN {total:.1f}s
║  Marts  → data/mart/          ({len(list(Path('data/mart').glob('*.csv')))} fichiers CSV)
║  DB     → data/github_analytics.db
║  Log    → {LOG_FILE}
╚══════════════════════════════════════════════════════════╝""")


if __name__ == "__main__":
    run_pipeline()