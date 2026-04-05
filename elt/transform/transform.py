"""
ELT — TRANSFORM
Nettoyage, typage, enrichissement et feature engineering sur raw_repos.
Spécificités GitHub : parsing topics, calcul d'âge, ratios d'engagement, etc.
"""

import pandas as pd
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [TRANSFORM] %(message)s")
log = logging.getLogger(__name__)

DB_PATH  = Path("data/github_analytics.db")
NOW      = datetime.now(timezone.utc)


def load_raw() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM raw_repos", conn)
    conn.close()
    log.info(f"{len(df):,} lignes chargées depuis raw_repos")
    return df


# ── Nettoyage ──────────────────────────────────────────────────────────────

def clean(df: pd.DataFrame) -> pd.DataFrame:
    log.info("--- Nettoyage ---")
    n0 = len(df)

    # Supprimer doublons sur Full Name
    df = df.drop_duplicates(subset=["Full Name"])
    log.info(f"Doublons supprimés : {n0 - len(df)}")

    # Colonnes critiques non nulles
    df = df.dropna(subset=["Repository Name", "Domain", "Stars Count", "Full Name"])

    # Types numériques
    for col in ["Stars Count", "Forks Count", "Watchers Count", "Open Issues Count", "Size (KB)"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # Valeurs aberrantes
    df = df[df["Stars Count"] >= 0]
    df = df[df["Forks Count"] >= 0]

    # Harmoniser chaînes
    df["Domain"]           = df["Domain"].str.strip()
    df["Owner Type"]       = df["Owner Type"].str.strip()
    df["Primary Language"] = df["Primary Language"].fillna("Unknown").str.strip()
    df["License"]          = df["License"].fillna("No License").str.strip()
    df["Topics"]           = df["Topics"].fillna("")

    # Booléens
    for col in ["Has Wiki", "Has Pages", "Has Projects"]:
        df[col] = df[col].astype(str).str.lower().map({"true": True, "false": False}).fillna(False)

    log.info(f"Lignes après nettoyage : {len(df):,} (supprimées : {n0 - len(df)})")
    return df


# ── Enrichissement ─────────────────────────────────────────────────────────

def enrich(df: pd.DataFrame) -> pd.DataFrame:
    log.info("--- Enrichissement ---")

    # ── Dates ────────────────────────────────────────────────────────────
    for col in ["Created At", "Updated At", "Pushed At"]:
        df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")

    df["created_year"]    = df["Created At"].dt.year
    df["created_month"]   = df["Created At"].dt.month
    df["created_quarter"] = df["Created At"].dt.quarter.map({1:"Q1",2:"Q2",3:"Q3",4:"Q4"})

    # Âge du repo en jours
    df["age_days"] = (NOW - df["Created At"]).dt.days
    df["age_years"] = (df["age_days"] / 365.25).round(1)

    # Jours depuis dernière mise à jour
    df["days_since_update"] = (NOW - df["Updated At"]).dt.days
    df["days_since_push"]   = (NOW - df["Pushed At"]).dt.days

    # ── Métriques d'engagement ────────────────────────────────────────────
    df["fork_ratio"]       = (df["Forks Count"] / df["Stars Count"].replace(0, 1)).round(4)
    df["issues_per_star"]  = (df["Open Issues Count"] / df["Stars Count"].replace(0, 1)).round(6)
    df["stars_per_day"]    = (df["Stars Count"] / df["age_days"].replace(0, 1)).round(2)
    df["forks_per_day"]    = (df["Forks Count"] / df["age_days"].replace(0, 1)).round(4)

    # ── Activité récente ──────────────────────────────────────────────────
    df["is_active"]        = df["days_since_push"] <= 90
    df["is_recently_updated"] = df["days_since_update"] <= 30
    df["is_stale"]         = df["days_since_push"] > 365

    # ── Segmentation stars ────────────────────────────────────────────────
    df["star_tier"] = pd.cut(
        df["Stars Count"],
        bins=[0, 5_000, 20_000, 50_000, 100_000, float("inf")],
        labels=["Rising (<5K)", "Popular (5K-20K)", "Trending (20K-50K)",
                "Hot (50K-100K)", "Legendary (100K+)"],
    )

    # ── Segmentation taille ───────────────────────────────────────────────
    df["size_tier"] = pd.cut(
        df["Size (KB)"],
        bins=[-1, 1_000, 10_000, 100_000, float("inf")],
        labels=["Tiny (<1MB)", "Small (1-10MB)", "Medium (10-100MB)", "Large (100MB+)"],
    )

    # ── Topics parsing ────────────────────────────────────────────────────
    df["topics_list"]  = df["Topics"].apply(
        lambda x: [t.strip() for t in str(x).split(",") if t.strip()] if x else []
    )
    df["topics_count"] = df["topics_list"].apply(len)
    df["has_topics"]   = df["topics_count"] > 0

    # ── Flags qualitatifs ─────────────────────────────────────────────────
    df["is_org"]              = df["Owner Type"] == "Organization"
    df["has_license"]         = df["License"] != "No License"
    df["is_open_source_friendly"] = df["has_license"] & df["Has Wiki"]

    # ── Score popularité synthétique (0–100) ─────────────────────────────
    # Normalisé : stars (60%) + forks (25%) + topics_count (15%)
    star_max   = df["Stars Count"].quantile(0.99)
    fork_max   = df["Forks Count"].quantile(0.99)
    topic_max  = df["topics_count"].max() or 1
    df["popularity_score"] = (
        0.60 * (df["Stars Count"].clip(upper=star_max) / star_max) +
        0.25 * (df["Forks Count"].clip(upper=fork_max) / fork_max) +
        0.15 * (df["topics_count"] / topic_max)
    ).mul(100).round(1)

    # Convertir dates en string pour SQLite
    for col in ["Created At", "Updated At", "Pushed At"]:
        df[col] = df[col].astype(str)

    log.info("Enrichissement terminé")
    return df


def save_processed(df: pd.DataFrame) -> None:
    # Sérialiser topics_list pour SQLite
    df_save = df.copy()
    df_save["topics_list"] = df_save["topics_list"].apply(lambda x: ",".join(x))
    conn = sqlite3.connect(DB_PATH)
    df_save.to_sql("processed_repos", conn, if_exists="replace", index=False)
    df_save.to_csv("data/processed/github_repos_processed.csv", index=False)
    log.info(f"{len(df_save):,} lignes → processed_repos + CSV")
    conn.close()


def run() -> pd.DataFrame:
    log.info("=== TRANSFORM START ===")
    df = load_raw()
    df = clean(df)
    df = enrich(df)
    save_processed(df)
    log.info("=== TRANSFORM DONE ===")
    return df


if __name__ == "__main__":
    run()