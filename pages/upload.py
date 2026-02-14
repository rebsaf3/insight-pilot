"""File upload page — upload data files, preview, and profile."""

import streamlit as st

from auth.session import require_permission, get_current_project_id, set_current_project
from services import file_service, data_profiler, credit_service
from db import queries


def show():
    user, ws = require_permission("upload_data")

    st.title("Upload Data")

    # Project selection
    project_id = get_current_project_id()
    projects = queries.get_projects_for_workspace(ws.id)
    if not projects:
        st.warning("Create a project first on the Projects page.")
        st.stop()

    project_names = {p.id: p.name for p in projects}
    project_ids = list(project_names.keys())
    default_idx = project_ids.index(project_id) if project_id in project_ids else 0

    selected_id = st.selectbox(
        "Select Project",
        project_ids,
        index=default_idx,
        format_func=lambda pid: project_names[pid],
    )
    if selected_id != project_id:
        set_current_project(selected_id)
        project_id = selected_id

    # Check upload limits
    allowed, limit_msg = credit_service.check_upload_allowed(user.id, ws.id)
    if not allowed:
        st.error(limit_msg)
        st.stop()

    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["csv", "xlsx", "xls", "json"],
        help="Supported formats: CSV, Excel (.xlsx/.xls), JSON",
    )

    if uploaded_file is None:
        # Show existing files for this project
        _show_existing_files(project_id)
        return

    # Validate file size
    file_bytes = uploaded_file.getvalue()
    size_ok, size_msg = credit_service.check_file_size_allowed(ws.id, len(file_bytes))
    if not size_ok:
        st.error(size_msg)
        return

    from config.settings import TIERS
    tier_config = TIERS.get(ws.tier, TIERS["free"])
    is_valid, err_msg = file_service.validate_upload(
        uploaded_file.name, len(file_bytes),
        max_size_mb=tier_config["max_file_size_mb"],
    )
    if not is_valid:
        st.error(err_msg)
        return

    file_format = file_service.detect_format(uploaded_file.name)

    # Process on button click
    if st.button("Upload & Analyze", type="primary", use_container_width=True):
        with st.spinner("Processing file..."):
            # Save to storage
            stored_filename, file_path = file_service.save_uploaded_file(
                file_bytes, uploaded_file.name, ws.id, project_id,
            )

            # Create DB record (initially 'pending')
            file_id = queries.create_uploaded_file(
                project_id=project_id,
                uploaded_by=user.id,
                original_filename=uploaded_file.name,
                stored_filename=stored_filename,
                file_path=file_path,
                file_format=file_format,
                file_size_bytes=len(file_bytes),
            )
            queries.update_file_status(file_id, "pending")

            # Load and profile
            try:
                df = file_service.load_dataframe(file_path, file_format)
                profile = data_profiler.profile_dataframe(df)

                queries.update_file_profile(
                    file_id=file_id,
                    row_count=profile["row_count"],
                    column_count=profile["column_count"],
                    column_names=list(df.columns),
                    data_profile=profile,
                )
                queries.update_file_status(file_id, "success")

                st.success(f"Uploaded **{uploaded_file.name}** — {profile['row_count']:,} rows, {profile['column_count']} columns")

                # Show preview
                _show_data_preview(df, profile)

            except Exception as e:
                queries.update_file_status(file_id, "error", str(e))
                st.error(f"Error processing file: {e}")

    # Show preview if file is selected (before upload)
    else:
        try:
            import io
            if file_format == "csv":
                df = file_service._load_csv(io.BytesIO(file_bytes))
            elif file_format in ("xlsx", "xls"):
                import pandas as pd
                df = pd.read_excel(io.BytesIO(file_bytes))
            elif file_format == "json":
                import pandas as pd
                df = pd.read_json(io.BytesIO(file_bytes))
            else:
                return

            st.subheader("Preview")
            st.dataframe(df.head(20), use_container_width=True)
            st.caption(f"{len(df):,} rows, {len(df.columns)} columns")

        except Exception as e:
            st.warning(f"Could not preview file: {e}")


def _show_data_preview(df, profile):
    """Show detailed data preview and profile."""
    st.subheader("Data Preview")
    st.dataframe(df.head(100), use_container_width=True)

    st.subheader("Data Profile")
    cols = st.columns(3)
    cols[0].metric("Rows", f"{profile['row_count']:,}")
    cols[1].metric("Columns", profile["column_count"])
    cols[2].metric("Memory", f"{profile['memory_usage_mb']:.1f} MB")

    st.subheader("Column Details")
    for col_info in profile["columns"]:
        with st.expander(f"**{col_info['name']}** ({col_info['dtype']})"):
            c1, c2, c3 = st.columns(3)
            c1.metric("Unique Values", col_info["unique_count"])
            c2.metric("Missing", f"{col_info['null_count']} ({col_info['null_pct']}%)")
            c3.metric("Type", col_info["dtype"])

            if col_info.get("stats"):
                st.json(col_info["stats"])

            if col_info["sample_values"]:
                st.caption(f"Sample values: {', '.join(col_info['sample_values'][:5])}")


def _status_badge_html(status: str) -> str:
    """Return an HTML badge for file upload status."""
    mapping = {
        "success": ("ip-badge ip-badge-success", "Success"),
        "error":   ("ip-badge ip-badge-error",   "Error"),
        "pending": ("ip-badge ip-badge-pending",  "Pending"),
    }
    cls, label = mapping.get(status, ("ip-badge ip-badge-info", status.title()))
    return f"<span class='{cls}'>{label}</span>"


def _show_existing_files(project_id):
    """Show files already uploaded to this project with status badges."""
    files = queries.get_files_for_project(project_id)
    if not files:
        st.info("No files uploaded yet. Upload a file above to get started.")
        return

    st.subheader("Uploaded Files")
    for f in files:
        status = getattr(f, "status", "success")
        badge = _status_badge_html(status)
        size_mb = f.file_size_bytes / (1024 * 1024)
        row_info = f"{f.row_count:,} rows" if f.row_count else ""
        error_info = ""
        if getattr(f, "error_message", None):
            error_info = (
                f"<div style='font-size:0.72rem;color:#DC2626;margin-top:2px'>"
                f"{f.error_message}</div>"
            )

        st.markdown(
            f"<div class='ip-card' style='padding:0.75rem 1rem;margin-bottom:0.5rem'>"
            f"<div style='display:flex;align-items:center;gap:0.75rem'>"
            f"<div style='flex:1'>"
            f"<div style='font-weight:600;font-size:0.88rem'>{f.original_filename}</div>"
            f"{error_info}"
            f"</div>"
            f"<div style='font-size:0.78rem;color:#57534E'>{row_info}</div>"
            f"<div style='font-size:0.78rem;color:#A8A29E'>{size_mb:.1f} MB</div>"
            f"{badge}"
            f"</div></div>",
            unsafe_allow_html=True,
        )


show()
