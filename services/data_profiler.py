"""Data profiling service — analyze DataFrame columns, types, statistics."""

import pandas as pd
import numpy as np


def profile_dataframe(df: pd.DataFrame) -> dict:
    """Generate a comprehensive profile of a DataFrame."""
    columns = []
    for col in df.columns:
        series = df[col]
        col_type = infer_column_type(series)

        col_info = {
            "name": col,
            "dtype": col_type,
            "pandas_dtype": str(series.dtype),
            "null_count": int(series.isnull().sum()),
            "null_pct": round(float(series.isnull().mean() * 100), 1),
            "unique_count": int(series.nunique()),
            "sample_values": _get_sample_values(series),
        }

        if col_type == "numeric":
            col_info["stats"] = _numeric_stats(series)
        elif col_type == "datetime":
            col_info["stats"] = _datetime_stats(series)

        columns.append(col_info)

    return {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": columns,
        "memory_usage_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
    }


def infer_column_type(series: pd.Series) -> str:
    """Infer semantic type: numeric, categorical, datetime, boolean, text."""
    if series.dtype == "bool" or set(series.dropna().unique()).issubset({True, False, 0, 1}):
        if series.nunique() <= 2:
            return "boolean"

    if pd.api.types.is_numeric_dtype(series):
        return "numeric"

    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    # Try to parse as datetime
    if series.dtype == "object":
        try:
            sample = series.dropna().head(20)
            if len(sample) > 0:
                pd.to_datetime(sample)
                return "datetime"
        except (ValueError, TypeError):
            pass

    # Categorical vs text heuristic
    if series.dtype == "object":
        unique_ratio = series.nunique() / max(len(series), 1)
        if unique_ratio < 0.5 or series.nunique() <= 50:
            return "categorical"
        return "text"

    return "categorical"


def _get_sample_values(series: pd.Series, n: int = 5) -> list:
    """Get first N unique non-null values as strings."""
    unique = series.dropna().unique()[:n]
    return [str(v) for v in unique]


def _numeric_stats(series: pd.Series) -> dict:
    """Calculate statistics for a numeric column."""
    clean = series.dropna()
    if len(clean) == 0:
        return {}
    return {
        "mean": round(float(clean.mean()), 2),
        "median": round(float(clean.median()), 2),
        "std": round(float(clean.std()), 2),
        "min": round(float(clean.min()), 2),
        "max": round(float(clean.max()), 2),
        "q25": round(float(clean.quantile(0.25)), 2),
        "q75": round(float(clean.quantile(0.75)), 2),
    }


def _datetime_stats(series: pd.Series) -> dict:
    """Calculate statistics for a datetime column."""
    try:
        dt = pd.to_datetime(series.dropna())
        if len(dt) == 0:
            return {}
        return {
            "min": str(dt.min()),
            "max": str(dt.max()),
            "range_days": (dt.max() - dt.min()).days,
        }
    except Exception:
        return {}


def profile_to_text_summary(profile: dict) -> str:
    """Convert a profile dict to a text summary for LLM prompts."""
    lines = [f"Dataset: {profile['row_count']:,} rows x {profile['column_count']} columns"]
    lines.append("Columns:")

    for col in profile["columns"]:
        parts = [f"  - {col['name']} ({col['dtype']})"]

        null_info = f"{col['null_count']} nulls"
        if col["null_pct"] > 0:
            null_info += f" ({col['null_pct']}%)"
        parts.append(null_info)

        parts.append(f"{col['unique_count']} unique")

        if col.get("stats"):
            stats = col["stats"]
            if col["dtype"] == "numeric":
                parts.append(f"range {stats.get('min', '?')}-{stats.get('max', '?')}, mean {stats.get('mean', '?')}")
            elif col["dtype"] == "datetime":
                parts.append(f"range {stats.get('min', '?')} to {stats.get('max', '?')}")

        if col["sample_values"]:
            samples = ", ".join(col["sample_values"][:3])
            parts.append(f"e.g. [{samples}]")

        lines.append(": ".join([parts[0], ", ".join(parts[1:])]))

    return "\n".join(lines)
