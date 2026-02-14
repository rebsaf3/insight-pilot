"""Tests for data profiler — column type inference and profiling."""

import pytest
import pandas as pd
from services.data_profiler import profile_dataframe, infer_column_type, profile_to_text_summary


class TestColumnTypeInference:
    def test_numeric_column(self):
        s = pd.Series([1, 2, 3, 4, 5])
        assert infer_column_type(s) == "numeric"

    def test_float_column(self):
        s = pd.Series([1.1, 2.2, 3.3])
        assert infer_column_type(s) == "numeric"

    def test_categorical_column(self):
        s = pd.Series(["A", "B", "A", "C", "B"])
        assert infer_column_type(s) == "categorical"

    def test_datetime_column(self):
        s = pd.Series(pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]))
        assert infer_column_type(s) == "datetime"

    def test_boolean_column(self):
        s = pd.Series([True, False, True, False])
        assert infer_column_type(s) == "boolean"

    def test_text_column(self):
        s = pd.Series(["This is a long text string that exceeds the threshold"] * 5)
        ctype = infer_column_type(s)
        assert ctype in ("text", "categorical")  # Depends on unique ratio


class TestProfileDataframe:
    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame({
            "name": ["Alice", "Bob", "Charlie", "Diana"],
            "age": [25, 30, 35, 28],
            "score": [88.5, 92.3, 78.1, 95.0],
            "active": [True, False, True, True],
        })

    def test_profile_has_correct_counts(self, sample_df):
        profile = profile_dataframe(sample_df)
        assert profile["row_count"] == 4
        assert profile["column_count"] == 4

    def test_profile_has_column_info(self, sample_df):
        profile = profile_dataframe(sample_df)
        assert "columns" in profile
        col_names = [c["name"] for c in profile["columns"]]
        assert "name" in col_names
        assert "age" in col_names
        assert "score" in col_names

    def test_numeric_column_has_stats(self, sample_df):
        profile = profile_dataframe(sample_df)
        age_col = next(c for c in profile["columns"] if c["name"] == "age")
        assert age_col["dtype"] == "numeric"
        assert "stats" in age_col
        assert "mean" in age_col["stats"]
        assert "min" in age_col["stats"]
        assert "max" in age_col["stats"]

    def test_profile_to_text(self, sample_df):
        profile = profile_dataframe(sample_df)
        text = profile_to_text_summary(profile)
        assert "4 rows" in text
        assert "4 columns" in text
        assert "age" in text


class TestEdgeCases:
    def test_empty_dataframe(self):
        df = pd.DataFrame()
        profile = profile_dataframe(df)
        assert profile["row_count"] == 0
        assert profile["column_count"] == 0

    def test_single_column_df(self):
        df = pd.DataFrame({"x": [1, 2, 3]})
        profile = profile_dataframe(df)
        assert profile["column_count"] == 1

    def test_df_with_nulls(self):
        df = pd.DataFrame({
            "a": [1, None, 3, None],
            "b": ["x", "y", None, "z"],
        })
        profile = profile_dataframe(df)
        a_col = next(c for c in profile["columns"] if c["name"] == "a")
        assert a_col["null_count"] == 2
