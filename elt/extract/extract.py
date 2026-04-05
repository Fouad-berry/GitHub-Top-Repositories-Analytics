"""
ELT — EXTRACT
Ingestion brute du CSV source dans la couche RAW (SQLite).
Principe ELT : on charge d'abord tel quel, on transforme ensuite.
"""

import pandas as pd
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [EXTRACT] %(message)s")
log = logging.getLogger(__name__)

RAW_CSV = Path("data/raw/github_top_repositories.csv")
DB_PATH = Path("data/github_analytics.db")


def extract() -> pd.DataFrame:
    """Lecture brute du CSV — aucune modification."""
    log.info(f"Source : {RAW_CSV}")
    df = pd.read_csv(RAW_CSV)
    log.info(f"{len(df):,} lignes | {df.shape[1]} colonnes")
    log.info(f"Colonnes : {list(df.columns)}")
    return df


def load_raw(df: pd.DataFrame) -> None:
    """Charge les données brutes telles quelles dans raw_repos."""
    conn = sqlite3.connect(DB_PATH)
    df["_extracted_at"] = datetime.utcnow().isoformat()
    df["_source_file"]  = RAW_CSV.name
    df.to_sql("raw_repos", conn, if_exists="replace", index=False)
    count = conn.execute("SELECT COUNT(*) FROM raw_repos").fetchone()[0]
    log.info(f"{count:,} lignes chargées dans raw_repos (DB : {DB_PATH})")
    conn.close()


def run() -> pd.DataFrame:
    log.info("=== EXTRACT START ===")
    df = extract()
    load_raw(df)
    log.info("=== EXTRACT DONE ===")
    return df


if __name__ == "__main__":
    run()