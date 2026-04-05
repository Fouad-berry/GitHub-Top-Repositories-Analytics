"""
analysis/eda.py — Analyse Exploratoire Complète
9 graphiques orientés GitHub Analytics
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import sqlite3
import warnings
from pathlib import Path
from collections import Counter

warnings.filterwarnings("ignore")

DB_PATH = Path("data/github_analytics.db")
FIG_DIR = Path("analysis/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)

PALETTE  = ["#0969DA", "#CF222E", "#1A7F37", "#9A6700", "#8250DF",
            "#EB6100", "#2DA44E", "#F6F8FA", "#57606A", "#1B7F37"]
GH_BLUE  = "#0969DA"

sns.set_theme(style="whitegrid", palette=PALETTE)
plt.rcParams.update({"figure.dpi": 120, "axes.spines.top": False,
                      "axes.spines.right": False, "font.size": 11})


def load() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM processed_repos", conn)
    conn.close()
    df["topics_list"] = df["topics_list"].apply(
        lambda x: [t.strip() for t in str(x).split(",") if t.strip()] if pd.notna(x) else []
    )
    return df


def sep(t): print(f"\n{'═'*60}\n  {t}\n{'═'*60}")


def overview(df):
    sep("VUE GÉNÉRALE")
    print(f"Repos        : {len(df):,}")
    print(f"Domaines     : {sorted(df['Domain'].unique())}")
    print(f"Langages     : {df['Primary Language'].nunique()} uniques")
    print(f"Stars range  : {df['Stars Count'].min():,} – {df['Stars Count'].max():,}")
    print(f"Années créa. : {df['created_year'].min()} – {df['created_year'].max()}")
    print(f"\nNaN :")
    nulls = df.isnull().sum()
    print(nulls[nulls > 0] if nulls.sum() > 0 else "  Aucun")


# ── Fig 1 : Stars par domaine ──────────────────────────────────────────────
def plot_domain_stars(df):
    d = df.groupby("Domain")["Stars Count"].sum().sort_values(ascending=True)
    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(d.index, d.values / 1e6, color=GH_BLUE, alpha=0.85)
    ax.bar_label(bars, labels=[f"{v:.1f}M" for v in d.values/1e6], padding=4, fontsize=9)
    ax.set_title("Total Stars par domaine", fontsize=14, fontweight="bold")
    ax.set_xlabel("Stars (millions)")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "01_stars_by_domain.png"); plt.close()
    print("✓ Fig 1 : Stars par domaine")


# ── Fig 2 : Top 15 langages ────────────────────────────────────────────────
def plot_language_repos(df):
    lang = df[df["Primary Language"] != "Unknown"]["Primary Language"]\
               .value_counts().head(15)
    fig, ax = plt.subplots(figsize=(11, 6))
    bars = ax.bar(lang.index, lang.values, color=PALETTE[:15])
    ax.bar_label(bars, padding=3, fontsize=9)
    ax.set_title("Top 15 langages par nombre de repos", fontsize=14, fontweight="bold")
    ax.set_ylabel("Nombre de repos")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "02_top_languages.png"); plt.close()
    print("✓ Fig 2 : Top langages")


# ── Fig 3 : Tendance création par année ───────────────────────────────────
def plot_creation_trend(df):
    yr = df.groupby("created_year").agg(
        nb_repos=("Full Name","count"),
        avg_stars=("Stars Count","mean")
    ).reset_index()
    yr = yr[yr["created_year"] >= 2010]
    fig, ax1 = plt.subplots(figsize=(12, 5))
    ax2 = ax1.twinx()
    ax1.bar(yr["created_year"], yr["nb_repos"], color=GH_BLUE, alpha=0.7, label="Nb repos")
    ax2.plot(yr["created_year"], yr["avg_stars"], color=PALETTE[1], marker="o",
             linewidth=2, label="Stars moyen")
    ax1.set_title("Création de repos dans le temps", fontsize=14, fontweight="bold")
    ax1.set_ylabel("Nombre de repos créés", color=GH_BLUE)
    ax2.set_ylabel("Stars moyen", color=PALETTE[1])
    ax1.set_xlabel("Année de création")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1+lines2, labels1+labels2, loc="upper left")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "03_creation_trend.png"); plt.close()
    print("✓ Fig 3 : Tendance création")


# ── Fig 4 : Distribution stars (log) ──────────────────────────────────────
def plot_stars_distribution(df):
    import numpy as np
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].hist(df["Stars Count"], bins=50, color=GH_BLUE, edgecolor="white", alpha=0.85)
    axes[0].set_title("Distribution des Stars (linéaire)", fontweight="bold")
    axes[0].set_xlabel("Stars")
    axes[1].hist(np.log1p(df["Stars Count"]), bins=50, color=PALETTE[4], edgecolor="white", alpha=0.85)
    axes[1].set_title("Distribution des Stars (log)", fontweight="bold")
    axes[1].set_xlabel("log(Stars + 1)")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "04_stars_distribution.png"); plt.close()
    print("✓ Fig 4 : Distribution stars")


# ── Fig 5 : Heatmap domaine × langage (top 8 langages) ───────────────────
def plot_heatmap(df):
    top_langs = df[df["Primary Language"]!="Unknown"]["Primary Language"]\
                    .value_counts().head(8).index.tolist()
    sub = df[df["Primary Language"].isin(top_langs)]
    pivot = sub.pivot_table(values="Stars Count", index="Domain",
                            columns="Primary Language", aggfunc="sum", fill_value=0)
    fig, ax = plt.subplots(figsize=(13, 8))
    sns.heatmap(pivot/1e3, annot=True, fmt=".0f", cmap="Blues", ax=ax,
                linewidths=0.5, cbar_kws={"label": "Stars (K)"})
    ax.set_title("Heatmap Stars (K) : Domaine × Langage", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "05_heatmap_domain_language.png"); plt.close()
    print("✓ Fig 5 : Heatmap domaine × langage")


# ── Fig 6 : Owner type ────────────────────────────────────────────────────
def plot_owner_type(df):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    ot_count = df["Owner Type"].value_counts()
    axes[0].pie(ot_count.values, labels=ot_count.index, autopct="%1.1f%%",
                colors=[GH_BLUE, PALETTE[1]], startangle=90)
    axes[0].set_title("Répartition Organization vs User", fontweight="bold")
    ot_stars = df.groupby("Owner Type")["Stars Count"].mean()
    axes[1].bar(ot_stars.index, ot_stars.values/1e3, color=[GH_BLUE, PALETTE[1]])
    axes[1].set_title("Stars moyen par type d'owner", fontweight="bold")
    axes[1].set_ylabel("Stars moyens (K)")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "06_owner_type.png"); plt.close()
    print("✓ Fig 6 : Owner type")


# ── Fig 7 : Star tier ────────────────────────────────────────────────────
def plot_star_tier(df):
    order = ["Rising (<5K)", "Popular (5K-20K)", "Trending (20K-50K)",
             "Hot (50K-100K)", "Legendary (100K+)"]
    tier = df.groupby("star_tier")["Full Name"].count().reindex(order, fill_value=0)
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(tier.index, tier.values, color=PALETTE[:5])
    ax.bar_label(bars, padding=3, fontsize=10)
    ax.set_title("Répartition par niveau de popularité (Stars)", fontsize=14, fontweight="bold")
    ax.set_ylabel("Nombre de repos")
    plt.xticks(rotation=15, ha="right")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "07_star_tier.png"); plt.close()
    print("✓ Fig 7 : Star tier")


# ── Fig 8 : Top 20 topics ─────────────────────────────────────────────────
def plot_topics(df):
    all_topics = []
    for t in df["topics_list"]:
        all_topics.extend(t)
    tc = pd.DataFrame(Counter(all_topics).most_common(20), columns=["topic","count"])
    fig, ax = plt.subplots(figsize=(11, 6))
    bars = ax.barh(tc["topic"][::-1], tc["count"][::-1], color=GH_BLUE, alpha=0.85)
    ax.bar_label(bars, padding=3, fontsize=9)
    ax.set_title("Top 20 Topics les plus fréquents", fontsize=14, fontweight="bold")
    ax.set_xlabel("Fréquence")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "08_top_topics.png"); plt.close()
    print("✓ Fig 8 : Top topics")


# ── Fig 9 : Activité — jours depuis dernier push ─────────────────────────
def plot_activity(df):
    act = df.groupby("Domain").agg(
        pct_active=("is_active","mean"),
        pct_stale =("is_stale","mean")
    ).reset_index().sort_values("pct_active", ascending=False)
    x = range(len(act))
    fig, ax = plt.subplots(figsize=(12, 6))
    width = 0.35
    ax.bar([i - width/2 for i in x], act["pct_active"]*100, width, label="Actif (push <90j)", color=PALETTE[2], alpha=0.85)
    ax.bar([i + width/2 for i in x], act["pct_stale"]*100,  width, label="Inactif (push >1an)", color=PALETTE[1], alpha=0.85)
    ax.set_xticks(list(x))
    ax.set_xticklabels(act["Domain"], rotation=30, ha="right")
    ax.set_title("% Repos actifs vs inactifs par domaine", fontsize=14, fontweight="bold")
    ax.set_ylabel("% repos")
    ax.legend()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "09_activity_by_domain.png"); plt.close()
    print("✓ Fig 9 : Activité par domaine")


def print_insights(df):
    sep("TOP INSIGHTS")
    top_repo  = df.loc[df["Stars Count"].idxmax()]
    top_domain= df.groupby("Domain")["Stars Count"].sum().idxmax()
    top_lang  = df[df["Primary Language"]!="Unknown"]["Primary Language"].value_counts().idxmax()
    print(f"Repo le + populaire : {top_repo['Full Name']} ({top_repo['Stars Count']:,} ⭐)")
    print(f"Domaine top stars   : {top_domain}")
    print(f"Langage le + commun : {top_lang}")
    print(f"% repos actifs      : {df['is_active'].mean()*100:.1f}%")
    print(f"% repos stales      : {df['is_stale'].mean()*100:.1f}%")
    print(f"% organisations     : {df['is_org'].mean()*100:.1f}%")
    print(f"Stars moyen/repo    : {df['Stars Count'].mean():,.0f}")
    print(f"Fork ratio moyen    : {df['fork_ratio'].mean():.3f}")
    print(f"Age moyen (ans)     : {df['age_years'].mean():.1f}")


if __name__ == "__main__":
    df = load()
    overview(df)
    sep("GÉNÉRATION FIGURES")
    plot_domain_stars(df)
    plot_language_repos(df)
    plot_creation_trend(df)
    plot_stars_distribution(df)
    plot_heatmap(df)
    plot_owner_type(df)
    plot_star_tier(df)
    plot_topics(df)
    plot_activity(df)
    print_insights(df)
    print(f"\n✅ Figures dans : {FIG_DIR}/")