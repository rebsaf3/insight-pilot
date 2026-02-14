"""Tests for code executor security — validates that dangerous code is blocked."""

import pytest
from services.code_executor import validate_code, execute_code, create_safe_globals
import pandas as pd


# ---------------------------------------------------------------------------
# AST Validation Tests
# ---------------------------------------------------------------------------

class TestValidateCode:
    """Test the AST-based code validation."""

    def test_valid_plotly_code(self):
        code = """
import plotly.express as px
fig = px.bar(df, x='category', y='value', title='Test Chart')
"""
        is_valid, error = validate_code(code)
        assert is_valid, f"Valid code rejected: {error}"

    def test_valid_plotly_go_code(self):
        code = """
import plotly.graph_objects as go
fig = go.Figure(data=[go.Bar(x=['A', 'B'], y=[1, 2])])
fig.update_layout(title='Test')
"""
        is_valid, error = validate_code(code)
        assert is_valid, f"Valid code rejected: {error}"

    def test_rejects_os_import(self):
        code = "import os\nfig = None"
        is_valid, error = validate_code(code)
        assert not is_valid
        assert "os" in error.lower() or "import" in error.lower()

    def test_rejects_subprocess_import(self):
        code = "import subprocess\nfig = None"
        is_valid, error = validate_code(code)
        assert not is_valid

    def test_rejects_sys_import(self):
        code = "import sys\nfig = None"
        is_valid, error = validate_code(code)
        assert not is_valid

    def test_rejects_open_call(self):
        code = """
data = open('/etc/passwd').read()
import plotly.express as px
fig = px.bar(df, x='a', y='b')
"""
        is_valid, error = validate_code(code)
        assert not is_valid

    def test_rejects_exec_call(self):
        code = """
exec('import os')
import plotly.express as px
fig = px.bar(df, x='a', y='b')
"""
        is_valid, error = validate_code(code)
        assert not is_valid

    def test_rejects_eval_call(self):
        code = """
eval('__import__("os")')
import plotly.express as px
fig = px.bar(df, x='a', y='b')
"""
        is_valid, error = validate_code(code)
        assert not is_valid

    def test_rejects_dunder_import(self):
        code = """
__import__('os')
import plotly.express as px
fig = px.bar(df, x='a', y='b')
"""
        is_valid, error = validate_code(code)
        assert not is_valid

    def test_rejects_no_fig_assignment(self):
        code = """
import plotly.express as px
chart = px.bar(df, x='a', y='b')
"""
        is_valid, error = validate_code(code)
        assert not is_valid
        assert "fig" in error.lower()

    def test_rejects_network_libraries(self):
        for lib in ["requests", "urllib", "httpx", "socket", "http"]:
            code = f"import {lib}\nimport plotly.express as px\nfig = px.bar(df, x='a', y='b')"
            is_valid, error = validate_code(code)
            assert not is_valid, f"Should reject import of {lib}"

    def test_rejects_file_system_operations(self):
        code = """
import plotly.express as px
with open('test.txt', 'w') as f:
    f.write('hack')
fig = px.bar(df, x='a', y='b')
"""
        is_valid, error = validate_code(code)
        assert not is_valid

    def test_allows_pandas_numpy(self):
        code = """
import pandas as pd
import numpy as np
import plotly.express as px
data = df.groupby('category').mean()
fig = px.bar(data, y='value')
"""
        is_valid, error = validate_code(code)
        assert is_valid, f"Should allow pandas/numpy: {error}"

    def test_rejects_syntax_error(self):
        code = "this is not valid python\nfig = None"
        is_valid, error = validate_code(code)
        assert not is_valid


# ---------------------------------------------------------------------------
# Execution Tests
# ---------------------------------------------------------------------------

class TestExecuteCode:
    """Test the sandboxed code execution."""

    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame({
            "category": ["A", "B", "C"],
            "value": [10, 20, 30],
        })

    def test_successful_execution(self, sample_df):
        code = """
import plotly.express as px
fig = px.bar(df, x='category', y='value', title='Test')
"""
        result = execute_code(code, sample_df)
        assert result["success"]
        assert result["figure"] is not None
        assert result["error"] is None

    def test_execution_with_error(self, sample_df):
        code = """
import plotly.express as px
fig = px.bar(df, x='nonexistent_column', y='value')
"""
        result = execute_code(code, sample_df)
        assert not result["success"]
        assert result["error"] is not None

    def test_df_is_read_only_copy(self, sample_df):
        """Ensure the original DataFrame is not modified."""
        original_values = sample_df["value"].tolist()
        code = """
import plotly.express as px
df['value'] = df['value'] * 100
fig = px.bar(df, x='category', y='value')
"""
        execute_code(code, sample_df)
        assert sample_df["value"].tolist() == original_values

    def test_safe_globals_restricted(self):
        """Verify safe globals don't include dangerous builtins."""
        df = pd.DataFrame({"a": [1]})
        safe = create_safe_globals(df)
        builtins = safe.get("__builtins__", {})

        # These should NOT be available (raw versions)
        for dangerous in ["open", "exec", "eval", "compile", "globals", "locals"]:
            assert dangerous not in builtins, f"Dangerous builtin '{dangerous}' should be blocked"

        # __import__ should be the restricted version, not the raw one
        if "__import__" in builtins:
            from services.code_executor import _safe_import
            assert builtins["__import__"] is _safe_import, "__import__ should be the restricted version"

        # These SHOULD be available
        for safe_fn in ["len", "range", "int", "float", "str", "list", "dict", "sorted", "max", "min"]:
            assert safe_fn in builtins, f"Safe builtin '{safe_fn}' should be available"


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_code(self):
        is_valid, error = validate_code("")
        assert not is_valid

    def test_whitespace_only_code(self):
        is_valid, error = validate_code("   \n\n  ")
        assert not is_valid

    def test_code_with_comments_only(self):
        is_valid, error = validate_code("# just a comment\n# another comment")
        assert not is_valid  # No fig assignment
