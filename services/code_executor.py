"""Safe code execution for Claude-generated Python code.

Security layers:
1. AST validation — reject non-whitelisted imports and dangerous calls
2. Restricted builtins — no open, exec, eval, __import__
3. Timeout via threading
4. Read-only data — df.copy() passed to exec
5. No disk/network — os, subprocess, requests blocked
"""

import ast
import threading
import time
import traceback
from typing import Optional

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config.settings import CODE_EXEC_TIMEOUT_SECONDS

# ---------------------------------------------------------------------------
# Whitelists and blocklists
# ---------------------------------------------------------------------------

ALLOWED_MODULES = {
    "pandas", "numpy", "plotly", "plotly.express", "plotly.graph_objects",
    "plotly.subplots", "datetime", "math", "statistics", "json", "re",
}

BLOCKED_BUILTINS = {
    "exec", "eval", "compile", "__import__", "open", "input",
    "breakpoint", "exit", "quit", "globals", "locals",
    "getattr", "setattr", "delattr", "vars", "dir",
    "memoryview", "bytearray",
}

BLOCKED_ATTR_PATTERNS = {
    "__import__", "__subclasses__", "__bases__", "__class__",
    "__globals__", "__code__", "__func__",
}


# ---------------------------------------------------------------------------
# AST Validation
# ---------------------------------------------------------------------------

def validate_code(code: str) -> tuple[bool, str]:
    """Static analysis of generated code before execution.
    Returns (is_safe, error_message)."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

    for node in ast.walk(tree):
        # Check imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in ALLOWED_MODULES:
                    return False, f"Import of '{alias.name}' is not allowed."

        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] not in ALLOWED_MODULES:
                return False, f"Import from '{node.module}' is not allowed."

        # Check for dangerous function calls
        elif isinstance(node, ast.Call):
            func_name = _get_call_name(node)
            if func_name:
                base = func_name.split(".")[0]
                if base in ("os", "sys", "subprocess", "shutil", "socket",
                            "requests", "urllib", "http", "ftplib", "pathlib"):
                    return False, f"Call to '{func_name}' is not allowed."
                if func_name in ("open", "exec", "eval", "compile", "__import__",
                                 "input", "breakpoint", "exit", "quit"):
                    return False, f"Call to '{func_name}' is not allowed."

        # Check for dangerous attribute access
        elif isinstance(node, ast.Attribute):
            if node.attr in BLOCKED_ATTR_PATTERNS:
                return False, f"Access to '{node.attr}' is not allowed."

    # Ensure code assigns to 'fig'
    assigns_fig = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "fig":
                    assigns_fig = True
        elif isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "fig":
                assigns_fig = True

    if not assigns_fig:
        return False, "Code must assign a plotly figure to a variable named 'fig'."

    return True, ""


def _get_call_name(node: ast.Call) -> Optional[str]:
    """Extract the function name from a Call node."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    elif isinstance(node.func, ast.Attribute):
        parts = []
        current = node.func
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return None


# ---------------------------------------------------------------------------
# Safe execution environment
# ---------------------------------------------------------------------------

def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    """A restricted __import__ that only allows whitelisted modules."""
    base = name.split(".")[0]
    if base not in ALLOWED_MODULES and name not in ALLOWED_MODULES:
        raise ImportError(f"Import of '{name}' is not allowed.")
    return __builtins__["__import__"](name, globals, locals, fromlist, level) if isinstance(__builtins__, dict) else __import__(name, globals, locals, fromlist, level)


def create_safe_globals(df: pd.DataFrame) -> dict:
    """Build the restricted globals dict for exec()."""
    import datetime
    import math
    import statistics
    import json
    import re

    # Filter builtins
    safe_builtins = {
        k: v for k, v in __builtins__.items()
        if k not in BLOCKED_BUILTINS
    } if isinstance(__builtins__, dict) else {
        k: getattr(__builtins__, k) for k in dir(__builtins__)
        if k not in BLOCKED_BUILTINS and not k.startswith("_")
    }

    # Add a restricted __import__ that only allows whitelisted modules
    safe_builtins["__import__"] = _safe_import

    return {
        "__builtins__": safe_builtins,
        "df": df.copy(),
        "pd": pd,
        "np": np,
        "px": px,
        "go": go,
        "make_subplots": make_subplots,
        "datetime": datetime,
        "math": math,
        "statistics": statistics,
        "json": json,
        "re": re,
    }


# ---------------------------------------------------------------------------
# Execution with timeout
# ---------------------------------------------------------------------------

def execute_code(code: str, df: pd.DataFrame,
                 timeout_seconds: int = None) -> dict:
    """Execute validated code in a restricted environment.

    Returns {
        'success': bool,
        'figure': Optional[go.Figure],
        'error': Optional[str],
        'execution_time_ms': int,
    }
    """
    if timeout_seconds is None:
        timeout_seconds = CODE_EXEC_TIMEOUT_SECONDS

    # Validate first
    is_safe, err = validate_code(code)
    if not is_safe:
        return {
            "success": False,
            "figure": None,
            "error": f"Code validation failed: {err}",
            "execution_time_ms": 0,
        }

    safe_globals = create_safe_globals(df)
    local_ns = {}
    result = {"success": False, "figure": None, "error": None, "execution_time_ms": 0}

    def _run():
        try:
            start = time.perf_counter()
            exec(code, safe_globals, local_ns)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            result["execution_time_ms"] = elapsed_ms

            fig = local_ns.get("fig") or safe_globals.get("fig")
            if fig is None:
                result["error"] = "Code did not produce a 'fig' variable."
                return

            if not isinstance(fig, go.Figure):
                result["error"] = f"'fig' is not a plotly Figure (got {type(fig).__name__})."
                return

            result["success"] = True
            result["figure"] = fig

        except Exception as e:
            result["error"] = f"{type(e).__name__}: {e}"
            result["execution_time_ms"] = 0

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=timeout_seconds)

    if thread.is_alive():
        result["error"] = f"Code execution timed out after {timeout_seconds} seconds."
        result["execution_time_ms"] = timeout_seconds * 1000

    return result
