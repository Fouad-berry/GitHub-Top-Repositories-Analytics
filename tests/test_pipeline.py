"""
tests/test_pipeline.py — Tests unitaires ELT GitHub Analytics
"""

import pandas as pd
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def raw_df():
    return pd.DataFrame({
        "Domain":           ["Machine Learning","Web Development","Machine Learning","DevOps","Machine Learning"],
        "Repository Name":  ["tensorflow","react","tensorflow","docker","pytorch"],
        "Full Name":        ["tensorflow/tensorflow","facebook/react","tensorflow/tensorflow","docker/docker","pytorch/pytorch"],
        "Description":      ["ML framework","UI library","ML framework","Container","DL framework"],
        "Primary Language": ["C++","JavaScript","C++","Go",None],
        "Stars Count":      [194000, 220000, 194000, 68000, 98000],
        "Forks Count":      [75000, 45000, 75000, 19000, 27000],
        "Watchers Count":   [194000, 220000, 194000, 68000, 98000],
        "Open Issues Count":[3715, 1200, 3715, 400, 18000],
        "Has Wiki":         ["True","True","True","False","True"],
        "Has Pages":        ["False","True","False","False","False"],
        "Has Projects":     ["True","True","True","True","True"],
        "Size (KB)":        [1288956, 250000, 1288956, 320000, 1273608],
        "Created At":       ["2015-11-07T01:19:20Z","2013-05-24T16:15:54Z","2015-11-07T01:19:20Z","2013-01-18T05:56:47Z","2016-08-13T05:26:41Z"],
        "Updated At":       ["2026-03-14T00:28:29Z","2026-03-14T01:00:00Z","2026-03-14T00:28:29Z","2026-03-10T00:00:00Z","2026-03-14T01:40:49Z"],
        "Pushed At":        ["2026-03-14T01:48:00Z","2026-03-14T02:00:00Z","2026-03-14T01:48:00Z","2025-01-01T00:00:00Z","2026-03-14T02:08:49Z"],
        "Default Branch":   ["master","main","master","master","main"],
        "Owner Login":      ["tensorflow","facebook","tensorflow","docker","pytorch"],
        "Owner Type":       ["Organization","Organization","Organization","Organization","Organization"],
        "License":          ["Apache License 2.0","MIT License","Apache License 2.0",None,"Other"],
        "Topics":           ["deep-learning,ml","react,frontend","deep-learning,ml","devops,containers","deep-learning,pytorch"],
    })


class TestClean:
    def test_removes_duplicates(self, raw_df):
        from elt.transform.transform import clean
        df = clean(raw_df)
        assert df["Full Name"].duplicated().sum() == 0

    def test_fills_unknown_language(self, raw_df):
        from elt.transform.transform import clean
        df = clean(raw_df)
        assert df["Primary Language"].isnull().sum() == 0
        assert "Unknown" in df["Primary Language"].values

    def test_fills_no_license(self, raw_df):
        from elt.transform.transform import clean
        df = clean(raw_df)
        assert df["License"].isnull().sum() == 0
        assert "No License" in df["License"].values

    def test_numeric_columns_non_negative(self, raw_df):
        from elt.transform.transform import clean
        df = clean(raw_df)
        for col in ["Stars Count", "Forks Count", "Open Issues Count"]:
            assert (df[col] >= 0).all()

    def test_boolean_columns_typed(self, raw_df):
        from elt.transform.transform import clean
        df = clean(raw_df)
        for col in ["Has Wiki", "Has Pages", "Has Projects"]:
            assert df[col].dtype == bool or df[col].isin([True, False]).all()


class TestEnrich:
    def _clean(self, raw_df):
        from elt.transform.transform import clean
        return clean(raw_df)

    def test_temporal_columns(self, raw_df):
        from elt.transform.transform import enrich
        df = enrich(self._clean(raw_df))
        for col in ["created_year","created_month","created_quarter","age_days","age_years"]:
            assert col in df.columns

    def test_age_days_positive(self, raw_df):
        from elt.transform.transform import enrich
        df = enrich(self._clean(raw_df))
        assert (df["age_days"] > 0).all()

    def test_fork_ratio_non_negative(self, raw_df):
        from elt.transform.transform import enrich
        df = enrich(self._clean(raw_df))
        assert (df["fork_ratio"] >= 0).all()

    def test_popularity_score_range(self, raw_df):
        from elt.transform.transform import enrich
        df = enrich(self._clean(raw_df))
        assert df["popularity_score"].between(0, 100).all()

    def test_topics_count_correct(self, raw_df):
        from elt.transform.transform import enrich
        df = enrich(self._clean(raw_df))
        # tensorflow a 2 topics : deep-learning, ml
        tf = df[df["Repository Name"] == "tensorflow"].iloc[0]
        assert tf["topics_count"] == 2

    def test_star_tier_no_nulls(self, raw_df):
        from elt.transform.transform import enrich
        df = enrich(self._clean(raw_df))
        assert df["star_tier"].isnull().sum() == 0

    def test_is_active_boolean(self, raw_df):
        from elt.transform.transform import enrich
        df = enrich(self._clean(raw_df))
        assert "is_active" in df.columns
        assert df["is_active"].isin([True, False]).all()

    def test_quarter_values(self, raw_df):
        from elt.transform.transform import enrich
        df = enrich(self._clean(raw_df))
        assert set(df["created_quarter"].unique()).issubset({"Q1","Q2","Q3","Q4"})


class TestDataQuality:
    def test_no_null_critical_columns(self, raw_df):
        from elt.transform.transform import clean
        df = clean(raw_df)
        for col in ["Repository Name","Domain","Stars Count","Full Name"]:
            assert df[col].isnull().sum() == 0

    def test_is_org_correct(self, raw_df):
        from elt.transform.transform import clean, enrich
        df = enrich(clean(raw_df))
        # Tous sont Organization dans notre fixture
        assert df["is_org"].all()

    def test_stars_per_day_non_negative(self, raw_df):
        from elt.transform.transform import clean, enrich
        df = enrich(clean(raw_df))
        assert (df["stars_per_day"] >= 0).all()