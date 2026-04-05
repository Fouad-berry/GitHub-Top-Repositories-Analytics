# 🐙 GitHub Top Repositories Analytics

> Pipeline ELT complet sur **3 000 dépôts GitHub** top-rated.  
> Architecture en couches (Staging → Intermediate → Marts) + Dashboard Power BI 5 pages.

---

## 📋 Table des matières

- [Aperçu](#aperçu)
- [Dataset](#dataset)
- [Architecture ELT](#architecture-elt)
- [Structure du projet](#structure-du-projet)
- [Installation](#installation)
- [Utilisation](#utilisation)
- [Data Marts](#data-marts)
- [Dashboard Power BI](#dashboard-power-bi)
- [Tests](#tests)
- [Insights clés](#insights-clés)

---

## Aperçu

Analyse des **3 000 dépôts GitHub les plus populaires** répartis sur **15 domaines** :
Machine Learning, JavaScript, Python, DevOps, Cybersecurity, Data Science, Rust, Go, etc.

Le pipeline ELT produit des métriques riches :
- **Score de popularité** synthétique (stars + forks + topics)
- **Métriques d'engagement** : fork ratio, stars/jour, issues/star
- **Segmentation** : tier de popularité, taille, activité
- **Feature engineering** : âge du repo, jours depuis dernier push, parsing topics

**Stack :**
```
Python · Pandas · SQLite · Power BI · pytest
```

---

## Dataset

**Fichier :** `data/raw/github_top_repositories.csv` — 3 000 lignes

| Colonne | Type | Description |
|---|---|---|
| `Domain` | str | Domaine tech (15 catégories) |
| `Repository Name` | str | Nom court du repo |
| `Full Name` | str | `owner/repo` |
| `Description` | str | Description du repo |
| `Primary Language` | str | Langage principal |
| `Stars Count` | int | Nombre d'étoiles |
| `Forks Count` | int | Nombre de forks |
| `Watchers Count` | int | Nombre de watchers |
| `Open Issues Count` | int | Issues ouvertes |
| `Has Wiki / Pages / Projects` | bool | Fonctionnalités activées |
| `Size (KB)` | int | Taille du repo |
| `Created / Updated / Pushed At` | datetime | Dates clés |
| `Default Branch` | str | Branche par défaut |
| `Owner Login` | str | Login du propriétaire |
| `Owner Type` | str | Organization ou User |
| `License` | str | Type de licence |
| `Topics` | str | Tags séparés par virgule |

**Domaines :** Android, Blockchain, C++, Cybersecurity, Data Science, Deep Learning, DevOps, Go, Java, JavaScript, Machine Learning, Python, Rust, Web Development, iOS

---

## Architecture ELT

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            PIPELINE ELT                                  │
│                                                                          │
│  ┌───────────────┐   ┌─────────────────┐   ┌────────────────────────┐  │
│  │   EXTRACT     │──▶│   LOAD (raw)    │──▶│      TRANSFORM         │  │
│  │               │   │                 │   │                        │  │
│  │  CSV → pandas │   │  raw_repos      │   │  Nettoyage             │  │
│  │  3 000 lignes │   │  (SQLite)       │   │  Typage / Dates        │  │
│  └───────────────┘   └─────────────────┘   │  Feature Engineering   │  │
│                                             │  Topics parsing        │  │
│                                             │  Score popularité      │  │
│                                             └────────────┬───────────┘  │
│                                                          │              │
│                         ┌────────────────────────────────┘              │
│                         ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                  LOAD — 3 COUCHES                               │    │
│  │                                                                 │    │
│  │  STAGING            INTERMEDIATE          MARTS                 │    │
│  │  ────────           ─────────────         ──────                │    │
│  │  stg_repos    ───► int_language_stats ──► mart_kpis             │    │
│  │               ───► int_domain_language──► mart_domain           │    │
│  │                                       ──► mart_language         │    │
│  │                                       ──► mart_owner_type       │    │
│  │                                       ──► mart_license          │    │
│  │                                       ──► mart_star_tier        │    │
│  │                                       ──► mart_creation_trend   │    │
│  │                                       ──► mart_activity_domain  │    │
│  │                                       ──► mart_engagement       │    │
│  │                                       ──► mart_topics_frequency │    │
│  │                                       ──► mart_top_repos        │    │
│  │                                       ──► mart_domain_lang_mat. │    │
│  │                                       ──► mart_default_branch   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
               ┌─────────────────────────────────────────┐
               │          POWER BI DASHBOARD             │
               │                                         │
               │  Page 1 : Overview                      │
               │  Page 2 : Popularité & Stars            │
               │  Page 3 : Tendances Temporelles         │
               │  Page 4 : Domaines & Langages           │
               │  Page 5 : Deep Dive & Topics            │
               └─────────────────────────────────────────┘
```

---

## Structure du projet

```
github_analytics/
│
├── data/
│   ├── raw/
│   │   └── github_top_repositories.csv    ← source (3 000 repos)
│   ├── processed/
│   │   └── github_repos_processed.csv     ← données enrichies (généré)
│   ├── mart/
│   │   ├── mart_kpis.csv
│   │   ├── mart_domain.csv
│   │   ├── mart_language.csv
│   │   ├── mart_owner_type.csv
│   │   ├── mart_license.csv
│   │   ├── mart_star_tier.csv
│   │   ├── mart_creation_trend.csv
│   │   ├── mart_activity_by_domain.csv
│   │   ├── mart_engagement.csv
│   │   ├── mart_topics_frequency.csv
│   │   ├── mart_top_repos.csv
│   │   ├── mart_domain_language_matrix.csv
│   │   ├── mart_default_branch.csv
│   │   ├── stg_repos.csv
│   │   ├── int_language_stats.csv
│   │   └── int_domain_language.csv
│   └── github_analytics.db               ← SQLite (généré)
│
├── elt/
│   ├── extract/
│   │   └── extract.py                    ← CSV → raw_repos
│   ├── transform/
│   │   └── transform.py                  ← nettoyage + feature engineering
│   └── load/
│       └── load.py                       ← staging + intermediate + marts
│
├── analysis/
│   ├── eda.py                            ← 9 graphiques EDA
│   └── figures/                          ← PNG générés
│
├── powerbi/
│   └── POWERBI_GUIDE.md                  ← guide DAX + 5 pages dashboard
│
├── tests/
│   └── test_pipeline.py                  ← 14 tests pytest
│
├── docs/
├── logs/
├── pipeline.py                           ← orchestrateur ELT
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Installation

```bash
# 1. Cloner
git clone https://github.com/ton-username/github-analytics.git
cd github-analytics

# 2. Environnement virtuel
python -m venv venv
source venv/bin/activate      # Mac/Linux
# venv\Scripts\activate       # Windows

# 3. Dépendances
pip install -r requirements.txt
```

---

## Utilisation

### Pipeline ELT complet

```bash
python pipeline.py
```

**Output attendu :**
```
╔══════════════════════════════════════════════════════════╗
║      GITHUB ANALYTICS — DATA ANALYSIS PIPELINE          ║
╚══════════════════════════════════════════════════════════╝
[EXTRACT]    3,000 lignes | 21 colonnes
[TRANSFORM]  Nettoyage + Feature Engineering terminé
[LOAD]       16 tables créées (staging + intermediate + marts)
PIPELINE TERMINÉ EN ~Xs
```

### Étapes séparées

```bash
python elt/extract/extract.py
python elt/transform/transform.py
python elt/load/load.py
```

### Analyse exploratoire

```bash
python analysis/eda.py
# → 9 graphiques dans analysis/figures/
```

---

## Data Marts

| Mart | Description | Lignes |
|---|---|---|
| `mart_kpis` | KPIs globaux (15 métriques) | 1 |
| `mart_domain` | Stats par domaine tech | 15 |
| `mart_language` | Stats par langage | ~30 |
| `mart_owner_type` | Org vs User | 2 |
| `mart_license` | Top 20 licences | 20 |
| `mart_star_tier` | 5 niveaux popularité | 5 |
| `mart_creation_trend` | Évolution trimestrielle | ~60 |
| `mart_activity_by_domain` | Activité par domaine | 15 |
| `mart_engagement` | Fork ratio, topics, wiki... | 15 |
| `mart_topics_frequency` | Top 100 topics | 100 |
| `mart_top_repos` | Top 200 repos par stars | 200 |
| `mart_domain_language_matrix` | Heatmap (pivot) | 15 |
| `mart_default_branch` | main vs master | 10 |

---

## Feature Engineering

Colonnes calculées ajoutées lors de la transformation :

| Feature | Description |
|---|---|
| `age_days` | Jours depuis la création |
| `age_years` | Années depuis la création |
| `days_since_update` | Jours depuis dernier update |
| `days_since_push` | Jours depuis dernier push |
| `fork_ratio` | Forks / Stars |
| `stars_per_day` | Stars / age_days |
| `issues_per_star` | Issues / Stars |
| `topics_count` | Nombre de topics |
| `is_active` | Push < 90 jours |
| `is_stale` | Push > 1 an |
| `star_tier` | 5 segments (Rising → Legendary) |
| `popularity_score` | Score 0-100 (stars 60% + forks 25% + topics 15%) |

---

## Dashboard Power BI

Voir [`powerbi/POWERBI_GUIDE.md`](powerbi/POWERBI_GUIDE.md) pour :
- Import des données step-by-step
- Modèle de données et relations
- Mesures DAX complètes
- Architecture des 5 pages
- Palette GitHub officielle

---

## Tests

```bash
pytest tests/ -v
```

**14 tests couvrent :**
- Suppression des doublons
- Valeurs manquantes (langue, licence)
- Types numériques
- Colonnes temporelles
- Score popularité dans [0, 100]
- Parsing des topics
- Fork ratio non négatif
- Validité des quarters

---

## Insights clés

- **Repo le + populaire :** freeCodeCamp (~409K ⭐)
- **Domaine dominant :** Machine Learning (total stars)
- **Langage le + fréquent :** Python (605 repos)
- **% repos actifs** (push < 90j) : calculé dynamiquement
- **Tendance :** explosion de la création de repos post-2019

---

## Roadmap

- [ ] Connexion GitHub API pour données en temps réel
- [ ] Orchestration Airflow
- [ ] dbt pour les transformations SQL
- [ ] Tests Great Expectations
- [ ] CI/CD GitHub Actions

---

## Auteur

Réalisé par **Fouad MOUTAIROU** 
Stack : Python · Pandas · SQLite · Power BI · pytest

---

*3 000 repos · 15 domaines · ~30 langages · Stars : 109 → 409 518*