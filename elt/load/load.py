"""
ELT — LOAD (DATA MARTS)
Construction des tables agrégées en 3 couches : Staging → Intermediate → Marts.
Architecture orientée Power BI — 13 marts spécialisés.
"""

import pandas as pd
import sqlite3
import logging
from pathlib import Path
from collections import Counter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [LOAD] %(message)s")
log = logging.getLogger(__name__)

DB_PATH  = Path("data/github_analytics.db")
MART_DIR = Path("data/mart")


def load_processed() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM processed_repos", conn)
    conn.close()
    # Reconstruire topics_list
    df["topics_list"] = df["topics_list"].apply(
        lambda x: [t.strip() for t in str(x).split(",") if t.strip()] if pd.notna(x) else []
    )
    log.info(f"{len(df):,} lignes chargées depuis processed_repos")
    return df


def save(df: pd.DataFrame, name: str, conn: sqlite3.Connection) -> None:
    df_save = df.copy()
    # Sérialiser les listes si présentes
    for col in df_save.columns:
        if df_save[col].apply(lambda x: isinstance(x, list)).any():
            df_save[col] = df_save[col].apply(lambda x: ",".join(x) if isinstance(x, list) else x)
    df_save.to_sql(name, conn, if_exists="replace", index=False)
    df_save.to_csv(MART_DIR / f"{name}.csv", index=False)
    log.info(f"  ✓ {name} : {len(df_save):,} lignes")


# ══════════════════════════════════════════════════════════════
# STAGING
# ══════════════════════════════════════════════════════════════

def build_staging(df: pd.DataFrame, conn: sqlite3.Connection):
    log.info("--- STAGING ---")
    stg = df[[
        "Full Name", "Repository Name", "Domain", "Primary Language",
        "Stars Count", "Forks Count", "Watchers Count", "Open Issues Count",
        "Size (KB)", "Owner Login", "Owner Type", "License",
        "Has Wiki", "Has Pages", "Has Projects",
        "Created At", "Updated At", "Pushed At",
        "Default Branch", "topics_count", "has_topics",
        "created_year", "created_month", "created_quarter",
        "age_days", "age_years", "days_since_update", "days_since_push",
        "fork_ratio", "issues_per_star", "stars_per_day", "forks_per_day",
        "is_active", "is_recently_updated", "is_stale",
        "star_tier", "size_tier",
        "is_org", "has_license", "is_open_source_friendly",
        "popularity_score",
    ]].copy()
    save(stg, "stg_repos", conn)


# ══════════════════════════════════════════════════════════════
# INTERMEDIATE
# ══════════════════════════════════════════════════════════════

def build_intermediate(df: pd.DataFrame, conn: sqlite3.Connection):
    log.info("--- INTERMEDIATE ---")

    # int_language_stats : stats complètes par langage
    int_lang = (
        df.groupby("Primary Language")
        .agg(
            nb_repos        =("Full Name", "count"),
            total_stars     =("Stars Count", "sum"),
            total_forks     =("Forks Count", "sum"),
            avg_stars       =("Stars Count", "mean"),
            median_stars    =("Stars Count", "median"),
            avg_fork_ratio  =("fork_ratio", "mean"),
            avg_age_years   =("age_years", "mean"),
            pct_active      =("is_active", "mean"),
            avg_topics      =("topics_count", "mean"),
            avg_score       =("popularity_score", "mean"),
        )
        .round(2)
        .reset_index()
        .sort_values("total_stars", ascending=False)
    )
    save(int_lang, "int_language_stats", conn)

    # int_domain_language : croisement domaine × langage
    int_dl = (
        df.groupby(["Domain", "Primary Language"])
        .agg(nb_repos=("Full Name","count"), avg_stars=("Stars Count","mean"))
        .round(1)
        .reset_index()
        .sort_values(["Domain","nb_repos"], ascending=[True, False])
    )
    save(int_dl, "int_domain_language", conn)


# ══════════════════════════════════════════════════════════════
# MARTS
# ══════════════════════════════════════════════════════════════

def build_marts(df: pd.DataFrame, conn: sqlite3.Connection):
    log.info("--- MARTS ---")

    # ── mart_kpis ────────────────────────────────────────────────────────
    kpis = pd.DataFrame([{
        "total_repos"           : len(df),
        "total_stars"           : int(df["Stars Count"].sum()),
        "total_forks"           : int(df["Forks Count"].sum()),
        "avg_stars"             : round(df["Stars Count"].mean(), 0),
        "median_stars"          : round(df["Stars Count"].median(), 0),
        "max_stars"             : int(df["Stars Count"].max()),
        "avg_age_years"         : round(df["age_years"].mean(), 1),
        "pct_active_repos"      : round(df["is_active"].mean() * 100, 1),
        "pct_org_repos"         : round(df["is_org"].mean() * 100, 1),
        "pct_with_license"      : round(df["has_license"].mean() * 100, 1),
        "avg_fork_ratio"        : round(df["fork_ratio"].mean(), 4),
        "total_open_issues"     : int(df["Open Issues Count"].sum()),
        "unique_languages"      : int(df["Primary Language"].nunique()),
        "unique_domains"        : int(df["Domain"].nunique()),
        "avg_popularity_score"  : round(df["popularity_score"].mean(), 1),
    }])
    save(kpis, "mart_kpis", conn)

    # ── mart_domain ──────────────────────────────────────────────────────
    domain = (
        df.groupby("Domain")
        .agg(
            nb_repos       =("Full Name", "count"),
            total_stars    =("Stars Count", "sum"),
            total_forks    =("Forks Count", "sum"),
            avg_stars      =("Stars Count", "mean"),
            max_stars      =("Stars Count", "max"),
            avg_age_years  =("age_years", "mean"),
            pct_active     =("is_active", "mean"),
            avg_score      =("popularity_score", "mean"),
            avg_topics     =("topics_count", "mean"),
            pct_org        =("is_org", "mean"),
        )
        .round(2)
        .reset_index()
        .sort_values("total_stars", ascending=False)
    )
    domain["stars_share_pct"] = (domain["total_stars"] / domain["total_stars"].sum() * 100).round(2)
    save(domain, "mart_domain", conn)

    # ── mart_language ────────────────────────────────────────────────────
    lang = (
        df.groupby("Primary Language")
        .agg(
            nb_repos       =("Full Name", "count"),
            total_stars    =("Stars Count", "sum"),
            avg_stars      =("Stars Count", "mean"),
            median_stars   =("Stars Count", "median"),
            avg_forks      =("Forks Count", "mean"),
            avg_fork_ratio =("fork_ratio", "mean"),
            pct_active     =("is_active", "mean"),
            avg_score      =("popularity_score", "mean"),
        )
        .round(2)
        .reset_index()
        .sort_values("nb_repos", ascending=False)
    )
    save(lang, "mart_language", conn)

    # ── mart_owner_type ──────────────────────────────────────────────────
    owner = (
        df.groupby("Owner Type")
        .agg(
            nb_repos    =("Full Name", "count"),
            total_stars =("Stars Count", "sum"),
            avg_stars   =("Stars Count", "mean"),
            avg_score   =("popularity_score", "mean"),
            pct_active  =("is_active", "mean"),
            pct_licensed=("has_license", "mean"),
        )
        .round(2)
        .reset_index()
    )
    save(owner, "mart_owner_type", conn)

    # ── mart_license ─────────────────────────────────────────────────────
    lic = (
        df.groupby("License")
        .agg(
            nb_repos    =("Full Name", "count"),
            total_stars =("Stars Count", "sum"),
            avg_stars   =("Stars Count", "mean"),
            avg_score   =("popularity_score", "mean"),
        )
        .round(2)
        .reset_index()
        .sort_values("nb_repos", ascending=False)
        .head(20)
    )
    lic["repos_share_pct"] = (lic["nb_repos"] / lic["nb_repos"].sum() * 100).round(2)
    save(lic, "mart_license", conn)

    # ── mart_star_tier ───────────────────────────────────────────────────
    star_tier = (
        df.groupby("star_tier")
        .agg(
            nb_repos      =("Full Name", "count"),
            total_stars   =("Stars Count", "sum"),
            avg_stars     =("Stars Count", "mean"),
            avg_forks     =("Forks Count", "mean"),
            avg_fork_ratio=("fork_ratio", "mean"),
            avg_score     =("popularity_score", "mean"),
            pct_active    =("is_active", "mean"),
            pct_org       =("is_org", "mean"),
        )
        .round(2)
        .reset_index()
    )
    save(star_tier, "mart_star_tier", conn)

    # ── mart_creation_trend ──────────────────────────────────────────────
    trend = (
        df.groupby(["created_year", "created_quarter"])
        .agg(
            nb_repos    =("Full Name", "count"),
            avg_stars   =("Stars Count", "mean"),
            avg_forks   =("Forks Count", "mean"),
            avg_score   =("popularity_score", "mean"),
            pct_org     =("is_org", "mean"),
            pct_licensed=("has_license", "mean"),
        )
        .round(2)
        .reset_index()
        .sort_values(["created_year", "created_quarter"])
    )
    trend["label"] = trend["created_year"].astype(str) + " " + trend["created_quarter"].astype(str)
    save(trend, "mart_creation_trend", conn)

    # ── mart_activity_status ─────────────────────────────────────────────
    act_domain = (
        df.groupby("Domain")
        .agg(
            nb_active  =("is_active",             "sum"),
            nb_stale   =("is_stale",              "sum"),
            nb_total   =("Full Name",             "count"),
            avg_days_push=("days_since_push",     "mean"),
        )
        .round(1)
        .reset_index()
    )
    act_domain["pct_active"] = (act_domain["nb_active"] / act_domain["nb_total"] * 100).round(1)
    act_domain["pct_stale"]  = (act_domain["nb_stale"]  / act_domain["nb_total"] * 100).round(1)
    save(act_domain, "mart_activity_by_domain", conn)

    # ── mart_domain_language_matrix ──────────────────────────────────────
    matrix = df.pivot_table(
        values="Stars Count",
        index="Domain",
        columns="Primary Language",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()
    save(matrix, "mart_domain_language_matrix", conn)

    # ── mart_top_repos ───────────────────────────────────────────────────
    top = (
        df.nlargest(200, "Stars Count")[[
            "Full Name", "Repository Name", "Domain", "Primary Language",
            "Stars Count", "Forks Count", "Open Issues Count",
            "License", "Owner Type", "age_years", "days_since_push",
            "fork_ratio", "stars_per_day", "topics_count",
            "is_active", "popularity_score", "star_tier",
        ]]
        .copy()
        .reset_index(drop=True)
    )
    top.insert(0, "rank", range(1, len(top)+1))
    save(top, "mart_top_repos", conn)

    # ── mart_engagement ──────────────────────────────────────────────────
    eng = (
        df.groupby("Domain")
        .agg(
            avg_fork_ratio    =("fork_ratio", "mean"),
            avg_issues_per_star=("issues_per_star", "mean"),
            avg_stars_per_day =("stars_per_day", "mean"),
            avg_topics_count  =("topics_count", "mean"),
            pct_has_wiki      =("Has Wiki", "mean"),
            pct_has_pages     =("Has Pages", "mean"),
            pct_has_projects  =("Has Projects", "mean"),
        )
        .round(4)
        .reset_index()
    )
    save(eng, "mart_engagement", conn)

    # ── mart_topics_frequency ────────────────────────────────────────────
    all_topics = []
    for topics in df["topics_list"]:
        all_topics.extend(topics)
    topic_counts = Counter(all_topics).most_common(100)
    topics_df = pd.DataFrame(topic_counts, columns=["topic", "frequency"])
    topics_df["rank"] = range(1, len(topics_df)+1)
    save(topics_df, "mart_topics_frequency", conn)

    # ── mart_default_branch ──────────────────────────────────────────────
    branch = (
        df.groupby("Default Branch")
        .agg(nb_repos=("Full Name","count"), avg_stars=("Stars Count","mean"))
        .round(1)
        .reset_index()
        .sort_values("nb_repos", ascending=False)
        .head(10)
    )
    save(branch, "mart_default_branch", conn)


def run():
    log.info("=== LOAD START ===")
    conn = sqlite3.connect(DB_PATH)
    df = load_processed()
    build_staging(df, conn)
    build_intermediate(df, conn)
    build_marts(df, conn)
    conn.close()
    log.info("=== LOAD DONE ===")


if __name__ == "__main__":
    run()