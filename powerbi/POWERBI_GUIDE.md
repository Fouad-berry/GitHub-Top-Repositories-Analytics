# 📊 Guide Power BI — GitHub Top Repositories Dashboard

## 1. Import des données

### Fichiers CSV à importer (`data/mart/`)

| Fichier | Table Power BI | Usage |
|---|---|---|
| `mart_kpis.csv` | KPIs | Cartes scorecards |
| `mart_domain.csv` | Domain | Analyses par domaine |
| `mart_language.csv` | Language | Analyses par langage |
| `mart_owner_type.csv` | OwnerType | Org vs User |
| `mart_license.csv` | License | Licences |
| `mart_star_tier.csv` | StarTier | Niveaux popularité |
| `mart_creation_trend.csv` | CreationTrend | Évolution temporelle |
| `mart_activity_by_domain.csv` | ActivityDomain | Activité repos |
| `mart_engagement.csv` | Engagement | Métriques engagement |
| `mart_topics_frequency.csv` | Topics | Topics populaires |
| `mart_top_repos.csv` | TopRepos | Top 200 repos |
| `mart_domain_language_matrix.csv` | DomainLangMatrix | Heatmap |
| `stg_orders.csv` (stg_repos) | AllRepos | Table détail |

**Import :** `Accueil → Obtenir des données → Texte/CSV`  
Charger chaque fichier, vérifier les types dans Power Query.

---

## 2. Modèle de données

```
AllRepos ──[Domain]──────────────────► Domain
         ──[Primary Language]────────► Language
         ──[Owner Type]──────────────► OwnerType
         ──[License]─────────────────► License
         ──[star_tier]───────────────► StarTier
         ──[created_year+quarter]────► CreationTrend
```

Toutes les relations : **Many-to-One**, direction filtre **Single**.

---

## 3. Mesures DAX

Crée une table `_Measures` (vide) et ajoute :

```dax
// ── KPIs ──────────────────────────────────────────────────────

Total Repos =
    COUNTROWS(AllRepos)

Total Stars =
    SUM(AllRepos[Stars Count])

Avg Stars per Repo =
    AVERAGE(AllRepos[Stars Count])

Median Stars =
    MEDIAN(AllRepos[Stars Count])

Avg Fork Ratio =
    AVERAGE(AllRepos[fork_ratio])

Avg Popularity Score =
    AVERAGE(AllRepos[popularity_score])

// ── Activité ───────────────────────────────────────────────────

% Active Repos =
    DIVIDE(
        CALCULATE(COUNTROWS(AllRepos), AllRepos[is_active] = TRUE()),
        COUNTROWS(AllRepos)
    ) * 100

% Stale Repos =
    DIVIDE(
        CALCULATE(COUNTROWS(AllRepos), AllRepos[is_stale] = TRUE()),
        COUNTROWS(AllRepos)
    ) * 100

% Recently Updated =
    DIVIDE(
        CALCULATE(COUNTROWS(AllRepos), AllRepos[is_recently_updated] = TRUE()),
        COUNTROWS(AllRepos)
    ) * 100

// ── Propriété ─────────────────────────────────────────────────

% Org Repos =
    DIVIDE(
        CALCULATE(COUNTROWS(AllRepos), AllRepos[Owner Type] = "Organization"),
        COUNTROWS(AllRepos)
    ) * 100

% With License =
    DIVIDE(
        CALCULATE(COUNTROWS(AllRepos), AllRepos[has_license] = TRUE()),
        COUNTROWS(AllRepos)
    ) * 100

// ── Stars par domaine (pour ranking dynamique) ─────────────────

Stars Rank by Domain =
    RANKX(
        ALL(Domain[Domain]),
        CALCULATE(SUM(AllRepos[Stars Count])),
        ,
        DESC
    )

// ── Top N repos dynamique ──────────────────────────────────────

Top N Stars Filter =
VAR N = SELECTEDVALUE('N Selector'[Value], 10)
RETURN
    RANKX(
        ALL(AllRepos[Full Name]),
        [Total Stars],
        ,
        DESC,
        DENSE
    ) <= N

// ── Évolution YoY ─────────────────────────────────────────────

Repos Created YoY % =
VAR curr = SELECTEDVALUE(CreationTrend[created_year])
VAR curr_count = CALCULATE(
    COUNTROWS(AllRepos),
    AllRepos[created_year] = curr
)
VAR prev_count = CALCULATE(
    COUNTROWS(AllRepos),
    AllRepos[created_year] = curr - 1
)
RETURN
    DIVIDE(curr_count - prev_count, prev_count) * 100
```

---

## 4. Architecture du Dashboard — 5 pages

### Page 1 — 🏠 Overview (Vue d'ensemble)
```
┌──────────┬──────────┬──────────┬──────────┬──────────┐
│  Total   │  Total   │  Avg     │  % Active│  % Org   │  ← Cards
│  Repos   │  Stars   │  Stars   │  Repos   │  Repos   │
│  3,000   │  XXM ⭐  │  XX,XXX  │  XX%     │  XX%     │
└──────────┴──────────┴──────────┴──────────┴──────────┘
┌─────────────────────────┬──────────────────────────────┐
│  Bar horizontal         │  Donut                        │
│  Total Stars / domaine  │  Répartition Org vs User      │
│  (Domain)               │  (OwnerType)                  │
└─────────────────────────┴──────────────────────────────┘
┌──────────────────────────────────────────────────────────┐
│  Bar chart : Top 15 langages par nb repos (Language)     │
└──────────────────────────────────────────────────────────┘
```

### Page 2 — ⭐ Popularité & Stars
```
┌─────────────────────────┬──────────────────────────────┐
│  Bar : Stars par tier   │  Scatter Plot                 │
│  (StarTier)             │  Stars vs Forks (AllRepos)    │
└─────────────────────────┴──────────────────────────────┘
┌──────────────────────────────────────────────────────────┐
│  Table : Top 200 repos (TopRepos)                        │
│  Rank | Repo | Domain | Language | Stars | Forks |       │
│  Score | Age | Active | Fork Ratio                       │
└──────────────────────────────────────────────────────────┘
```

### Page 3 — 📅 Tendances Temporelles
```
┌──────────────────────────────────────────────────────────┐
│  Line + Bar combo : Repos créés par an + Stars moyen     │
│  (CreationTrend)                                         │
└──────────────────────────────────────────────────────────┘
┌─────────────────────────┬──────────────────────────────┐
│  Area chart             │  Bar : % actifs vs stales     │
│  Repos cumulés          │  par domaine                  │
│  par trimestre          │  (ActivityDomain)             │
└─────────────────────────┴──────────────────────────────┘
```

### Page 4 — 🌍 Domaines & Langages
```
┌──────────────────────────────────────────────────────────┐
│  Heatmap (Matrix visual) : Stars par Domaine × Langage   │
│  (DomainLangMatrix)                                      │
└──────────────────────────────────────────────────────────┘
┌─────────────────────────┬──────────────────────────────┐
│  Clustered Bar          │  Bar : Engagement metrics     │
│  Avg Stars par domaine  │  Fork ratio, Topics count     │
│  + Avg Score            │  par domaine (Engagement)     │
└─────────────────────────┴──────────────────────────────┘
```

### Page 5 — 🔬 Deep Dive & Topics
```
┌─────────────────────────┬──────────────────────────────┐
│  Bar horizontal         │  Donut                        │
│  Top 20 Topics          │  Distribution licences        │
│  (Topics)               │  (License)                    │
└─────────────────────────┴──────────────────────────────┘
┌──────────────────────────────────────────────────────────┐
│  Table détail filtrable (AllRepos / stg_repos)           │
│  Filtres : Domaine | Langage | Star Tier | Actif/Stale   │
└──────────────────────────────────────────────────────────┘
```

---

## 5. Slicers recommandés (chaque page)

| Slicer | Source | Type |
|---|---|---|
| Domaine | `AllRepos[Domain]` | Dropdown/List |
| Langage | `AllRepos[Primary Language]` | Dropdown |
| Star Tier | `StarTier[star_tier]` | Buttons |
| Owner Type | `AllRepos[Owner Type]` | Buttons |
| Année création | `AllRepos[created_year]` | Between |
| Actif/Inactif | `AllRepos[is_active]` | Toggle |

---

## 6. Visuels spéciaux recommandés

| Visual | Usage | Config |
|---|---|---|
| **Word Cloud** (custom) | Topics fréquents | `mart_topics_frequency` |
| **Decomposition Tree** | Stars → Domaine → Langage → Repo | Drill-down |
| **Key Influencers** | Facteurs qui influencent les stars | `stg_repos` colonnes |
| **Smart Narrative** | Résumé auto des KPIs | Global |

---

## 7. Palette GitHub

| Couleur | Hex | Usage |
|---|---|---|
| GitHub Blue | `#0969DA` | Couleur principale |
| GitHub Green | `#1A7F37` | Actif, positif |
| GitHub Red | `#CF222E` | Stale, négatif |
| GitHub Purple | `#8250DF` | Score, ranking |
| GitHub Orange | `#EB6100` | Trending |
| Dark | `#24292F` | Textes sombres |
| Light | `#F6F8FA` | Fonds clairs |

---

## 8. Publication Power BI Service

```
Fichier → Publier → Workspace : "GitHub Analytics"
```

Configurer : actualisation planifiée si source live via GitHub API.