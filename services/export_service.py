"""Export service — PDF and PNG export of dashboards and charts."""

from typing import Optional
import io
import re

import pandas as pd
import plotly.io as pio
import plotly.graph_objects as go


def export_chart_as_image(plotly_json: str, fmt: str = "png",
                          width: int = 1200, height: int = 600) -> bytes:
    """Convert a plotly figure JSON to a static image. Returns image bytes."""
    fig = pio.from_json(plotly_json)
    return fig.to_image(format=fmt, width=width, height=height, engine="kaleido")


def export_dashboard_as_pdf(dashboard, charts: list) -> bytes:
    """Generate a PDF containing all charts from a dashboard.
    Returns PDF bytes."""
    from fpdf import FPDF
    import io
    import tempfile
    import os

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title page
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(0, 40, dashboard.name, new_x="LMARGIN", new_y="NEXT", align="C")
    if dashboard.description:
        pdf.set_font("Helvetica", "", 12)
        pdf.multi_cell(0, 8, dashboard.description, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 20, f"Generated on {dashboard.updated_at[:10]}", new_x="LMARGIN", new_y="NEXT", align="C")

    # Chart pages
    for chart in charts:
        if not chart.plotly_json:
            continue

        pdf.add_page("L")  # Landscape for charts

        # Chart title
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, chart.title, new_x="LMARGIN", new_y="NEXT")

        # Render chart to temp image
        try:
            img_bytes = export_chart_as_image(chart.plotly_json, width=1400, height=700)
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(img_bytes)
                tmp_path = tmp.name

            pdf.image(tmp_path, x=10, y=25, w=270)
            os.unlink(tmp_path)
        except Exception as e:
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 10, f"Error rendering chart: {e}", new_x="LMARGIN", new_y="NEXT")

        # Prompt
        pdf.set_y(pdf.get_y() + 5)
        pdf.set_font("Helvetica", "I", 9)
        prompt_text = chart.user_prompt[:200]
        pdf.multi_cell(0, 5, f"Prompt: {prompt_text}")

    return bytes(pdf.output())


def export_dashboard_as_images(dashboard, charts: list) -> list[tuple[str, bytes]]:
    """Export each chart as a separate PNG. Returns [(title, png_bytes), ...]."""
    results = []
    for chart in charts:
        if not chart.plotly_json:
            continue
        try:
            img_bytes = export_chart_as_image(chart.plotly_json)
            results.append((chart.title, img_bytes))
        except Exception:
            continue
    return results


def _safe_sheet_name(name: str) -> str:
    clean = re.sub(r"[\[\]\*\?\/\\:]", "_", (name or "Chart"))
    return clean[:31] or "Chart"


def export_dashboard_as_excel(dashboard, charts: list) -> bytes:
    """Export dashboard chart data to a multi-sheet XLSX workbook."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        meta = pd.DataFrame(
            [
                {"Field": "Dashboard", "Value": dashboard.name},
                {"Field": "Description", "Value": dashboard.description or ""},
                {"Field": "Generated At", "Value": dashboard.updated_at},
                {"Field": "Chart Count", "Value": len(charts)},
            ]
        )
        meta.to_excel(writer, sheet_name="Summary", index=False)

        for i, chart in enumerate(charts, start=1):
            if not chart.plotly_json:
                continue
            sheet = _safe_sheet_name(f"{i}_{chart.title}")
            fig = pio.from_json(chart.plotly_json)
            traces = fig.to_dict().get("data", [])

            rows = []
            for trace_idx, trace in enumerate(traces, start=1):
                list_keys = []
                max_len = 0
                for k, v in trace.items():
                    if isinstance(v, (list, tuple)):
                        list_keys.append(k)
                        max_len = max(max_len, len(v))
                if max_len == 0:
                    rows.append(
                        {
                            "trace_index": trace_idx,
                            "trace_name": trace.get("name", f"Trace {trace_idx}"),
                            "trace_type": trace.get("type", ""),
                        }
                    )
                    continue
                for row_idx in range(max_len):
                    row = {
                        "trace_index": trace_idx,
                        "trace_name": trace.get("name", f"Trace {trace_idx}"),
                        "trace_type": trace.get("type", ""),
                    }
                    for k in list_keys:
                        vals = trace.get(k, [])
                        row[k] = vals[row_idx] if row_idx < len(vals) else None
                    rows.append(row)
            if not rows:
                rows = [{"note": "No plottable trace points found for this chart."}]
            pd.DataFrame(rows).to_excel(writer, sheet_name=sheet, index=False)
    return output.getvalue()
