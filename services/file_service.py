"""File upload, storage, format detection, and parsing service."""

import uuid
from pathlib import Path
from typing import Optional

import pandas as pd

from config.settings import UPLOADS_DIR, ALLOWED_EXTENSIONS


def validate_upload(filename: str, file_size_bytes: int, max_size_mb: int) -> tuple[bool, str]:
    """Validate file extension and size. Returns (is_valid, error_message)."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
    max_bytes = max_size_mb * 1024 * 1024
    if file_size_bytes > max_bytes:
        return False, f"File too large ({file_size_bytes / 1024 / 1024:.1f} MB). Maximum: {max_size_mb} MB."
    return True, ""


def detect_format(filename: str) -> str:
    """Return format string based on file extension."""
    ext = Path(filename).suffix.lower()
    return {".csv": "csv", ".xlsx": "xlsx", ".xls": "xls", ".json": "json"}.get(ext, "unknown")


def save_uploaded_file(file_bytes: bytes, original_filename: str,
                       workspace_id: str, project_id: str) -> tuple[str, str]:
    """Save uploaded file to storage. Returns (stored_filename, relative_file_path)."""
    ext = Path(original_filename).suffix.lower()
    stored_filename = f"{uuid.uuid4().hex}{ext}"
    dir_path = UPLOADS_DIR / workspace_id / project_id
    dir_path.mkdir(parents=True, exist_ok=True)

    file_path = dir_path / stored_filename
    file_path.write_bytes(file_bytes)

    # Return path relative to UPLOADS_DIR
    relative_path = f"{workspace_id}/{project_id}/{stored_filename}"
    return stored_filename, relative_path


def load_dataframe(file_path: str, file_format: str) -> pd.DataFrame:
    """Read a stored file into a pandas DataFrame."""
    full_path = UPLOADS_DIR / file_path

    if file_format == "csv":
        return _load_csv(full_path)
    elif file_format in ("xlsx", "xls"):
        return _load_excel(full_path, file_format)
    elif file_format == "json":
        return _load_json(full_path)
    else:
        raise ValueError(f"Unsupported format: {file_format}")


def _load_csv(path: Path) -> pd.DataFrame:
    """Load CSV with encoding detection and delimiter sniffing."""
    # Try to detect encoding
    try:
        import chardet
        raw = path.read_bytes()
        detected = chardet.detect(raw[:10000])
        encoding = detected.get("encoding", "utf-8")
    except Exception:
        encoding = "utf-8"

    # Try detected encoding, fallback chain
    for enc in [encoding, "utf-8", "latin-1", "cp1252"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue

    return pd.read_csv(path, encoding="utf-8", errors="replace")


def _load_excel(path: Path, fmt: str) -> pd.DataFrame:
    """Load Excel file. Returns first sheet by default."""
    engine = "openpyxl" if fmt == "xlsx" else "xlrd"
    return pd.read_excel(path, engine=engine)


def _load_json(path: Path) -> pd.DataFrame:
    """Load JSON file. Handles both flat arrays and nested objects."""
    try:
        return pd.read_json(path)
    except ValueError:
        # Try json_normalize for nested structures
        import json
        data = json.loads(path.read_text())
        if isinstance(data, list):
            return pd.json_normalize(data)
        elif isinstance(data, dict):
            # Might be a dict with a data key
            for key in ("data", "results", "records", "items", "rows"):
                if key in data and isinstance(data[key], list):
                    return pd.json_normalize(data[key])
            return pd.json_normalize(data)
        raise


def get_excel_sheet_names(file_path: str, file_format: str) -> list[str]:
    """Get sheet names from an Excel file."""
    full_path = UPLOADS_DIR / file_path
    engine = "openpyxl" if file_format == "xlsx" else "xlrd"
    xl = pd.ExcelFile(full_path, engine=engine)
    return xl.sheet_names


def load_excel_sheet(file_path: str, file_format: str, sheet_name: str) -> pd.DataFrame:
    """Load a specific sheet from an Excel file."""
    full_path = UPLOADS_DIR / file_path
    engine = "openpyxl" if file_format == "xlsx" else "xlrd"
    return pd.read_excel(full_path, sheet_name=sheet_name, engine=engine)


def delete_stored_file(file_path: str) -> bool:
    """Remove a file from storage."""
    full_path = UPLOADS_DIR / file_path
    try:
        full_path.unlink(missing_ok=True)
        return True
    except Exception:
        return False
