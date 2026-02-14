"""Analysis wizard — 3-step flow: Describe → Review → Save."""

import streamlit as st

from auth.session import require_permission, get_current_project_id
from services import file_service, data_profiler, llm_service, code_executor, credit_service
from db import queries


def show():
    user, ws = require_permission("run_analysis")

    st.title("Analyze Data")

    project_id = get_current_project_id()
    if not project_id:
        st.warning("Select a project first from the Projects page.")
        st.stop()

    project = queries.get_project_by_id(project_id, ws.id)
    if not project:
        st.warning("Project not found. Select one from the Projects page.")
        st.stop()

    # Get files for this project
    files = queries.get_files_for_project(project_id)
    if not files:
        st.warning("No data files in this project. Upload data first.")
        st.stop()

    # File selector
    file_names = {f.id: f.original_filename for f in files}
    selected_file_id = st.selectbox(
        "Select Data File",
        list(file_names.keys()),
        format_func=lambda fid: file_names[fid],
    )
    selected_file = queries.get_file_by_id(selected_file_id)

    # Initialize wizard state
    if "wizard_step" not in st.session_state:
        st.session_state["wizard_step"] = 1
    if "wizard_file_id" not in st.session_state or st.session_state["wizard_file_id"] != selected_file_id:
        st.session_state["wizard_file_id"] = selected_file_id
        st.session_state["wizard_step"] = 1
        st.session_state.pop("wizard_code", None)
        st.session_state.pop("wizard_figure_json", None)
        st.session_state.pop("wizard_explanation", None)
        st.session_state.pop("wizard_prompt", None)
        st.session_state.pop("wizard_tokens_used", None)

    # Progress indicator
    step = st.session_state["wizard_step"]
    cols = st.columns(3)
    for i, (col, label) in enumerate(zip(cols, ["1. Describe", "2. Review", "3. Save"])):
        if i + 1 < step:
            col.success(label)
        elif i + 1 == step:
            col.info(label)
        else:
            col.markdown(f"<span style='color:#999'>{label}</span>", unsafe_allow_html=True)

    st.divider()

    if step == 1:
        _step_describe(user, ws, selected_file)
    elif step == 2:
        _step_review(user, ws, selected_file)
    elif step == 3:
        _step_save(user, ws, selected_file)


def _step_describe(user, ws, selected_file):
    """Step 1: Describe what you want."""
    # Show data profile summary
    if selected_file.data_profile:
        profile_text = data_profiler.profile_to_text_summary(selected_file.data_profile)
        with st.expander("Data Profile", expanded=False):
            st.code(profile_text)

    # Credit check
    has_credits, balance = credit_service.check_sufficient_credits(ws.id, 5)

    # Prompt input
    st.subheader("Describe Your Report")

    # Example prompts
    examples = [
        "Show revenue trends over time",
        "Compare sales by category as a bar chart",
        "Create a summary table of all columns",
        "Show the distribution of values",
        "Plot correlation between numeric columns",
    ]
    st.caption("Examples:")
    example_cols = st.columns(len(examples))
    for i, (col, ex) in enumerate(zip(example_cols, examples)):
        if col.button(ex, key=f"ex_{i}", use_container_width=True):
            st.session_state["wizard_prompt_input"] = ex

    prompt = st.text_area(
        "What would you like to see?",
        value=st.session_state.get("wizard_prompt_input", ""),
        height=120,
        placeholder="Describe the chart, report, or dashboard you want...",
    )

    # Credit estimate
    st.caption(f"Estimated cost: ~3-5 credits | Your balance: **{balance} credits**")

    # Generate button
    if not has_credits:
        st.error("Insufficient credits. Purchase more or upgrade your plan.")
        return

    if st.button("Generate", type="primary", use_container_width=True, disabled=not prompt):
        if not prompt:
            st.warning("Please describe what you want.")
            return

        _generate_chart(user, ws, selected_file, prompt)


def _generate_chart(user, ws, selected_file, prompt, is_revision=False):
    """Generate a chart from the prompt."""
    with st.spinner("Generating your report..."):
        try:
            # Load dataframe
            df = file_service.load_dataframe(selected_file.file_path, selected_file.file_format)
            profile = selected_file.data_profile

            # Call Claude
            result = llm_service.generate_chart_code(
                user_prompt=prompt,
                data_profile=profile,
                df=df,
            )

            code = result["code"]
            tokens_used = result["tokens_used"]
            total_tokens = tokens_used

            # Execute code
            exec_result = code_executor.execute_code(code, df)

            # Auto-retry on failure (up to 2 retries)
            retries = 0
            while not exec_result["success"] and retries < 2:
                retries += 1
                refine_result = llm_service.refine_chart_code(
                    original_prompt=prompt,
                    original_code=code,
                    error_message=exec_result["error"],
                    data_profile=profile,
                    df=df,
                )
                code = refine_result["code"]
                total_tokens += refine_result["tokens_used"]
                exec_result = code_executor.execute_code(code, df)

            # Deduct credits
            credit_cost = credit_service.calculate_credit_cost(total_tokens)
            credit_service.deduct_credits(
                workspace_id=ws.id,
                user_id=user.id,
                amount=credit_cost,
                reason="Chart generation" if not is_revision else "Chart revision",
            )

            # Save to prompt history
            queries.save_prompt_history(
                user_id=user.id,
                workspace_id=ws.id,
                project_id=selected_file.project_id,
                file_id=selected_file.id,
                prompt_text=prompt,
                response_code=code,
                response_error=exec_result.get("error"),
                tokens_used=total_tokens,
                model_used=result["model"],
            )

            if exec_result["success"]:
                # Store results in session state
                st.session_state["wizard_code"] = code
                st.session_state["wizard_figure_json"] = exec_result["figure"].to_json()
                st.session_state["wizard_explanation"] = result.get("explanation", "")
                st.session_state["wizard_prompt"] = prompt
                st.session_state["wizard_tokens_used"] = total_tokens
                st.session_state["wizard_credit_cost"] = credit_cost
                st.session_state["wizard_step"] = 2
                st.rerun()
            else:
                st.error(f"Code generation failed after {retries + 1} attempts: {exec_result['error']}")
                with st.expander("Generated Code"):
                    st.code(code, language="python")

        except Exception as e:
            st.error(f"Error: {e}")


def _step_review(user, ws, selected_file):
    """Step 2: Review the generated report."""
    import plotly.io as pio

    figure_json = st.session_state.get("wizard_figure_json")
    code = st.session_state.get("wizard_code")
    explanation = st.session_state.get("wizard_explanation")
    credit_cost = st.session_state.get("wizard_credit_cost", 0)

    if not figure_json:
        st.session_state["wizard_step"] = 1
        st.rerun()
        return

    # Render the chart
    fig = pio.from_json(figure_json)
    st.plotly_chart(fig, use_container_width=True)

    # Explanation
    if explanation:
        st.markdown(explanation)

    # Credit info
    balance = credit_service.get_balance(ws.id)
    st.caption(f"Used **{credit_cost} credits** | Remaining: **{balance} credits**")

    # Code preview
    with st.expander("View Generated Code"):
        st.code(code, language="python")

    # Action buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Accept & Save", type="primary", use_container_width=True):
            st.session_state["wizard_step"] = 3
            st.rerun()

    with col2:
        # Check if revisions are allowed
        can_revise, revise_msg = credit_service.check_revisions_allowed(ws.id)
        if can_revise:
            revision_prompt = st.text_input(
                "Request changes",
                placeholder="Make the bars horizontal, add data labels...",
                key="revision_input",
            )
            if st.button("Apply Changes", use_container_width=True, disabled=not revision_prompt):
                if revision_prompt:
                    # Re-generate with revision context
                    combined_prompt = f"Original request: {st.session_state['wizard_prompt']}\n\nRevision: {revision_prompt}"
                    _generate_chart(user, ws, selected_file, combined_prompt, is_revision=True)
        else:
            st.button("Request Changes", use_container_width=True, disabled=True,
                       help=revise_msg)

    with col3:
        if st.button("Start Over", use_container_width=True):
            st.session_state["wizard_step"] = 1
            st.session_state.pop("wizard_code", None)
            st.session_state.pop("wizard_figure_json", None)
            st.rerun()


def _step_save(user, ws, selected_file):
    """Step 3: Save to a dashboard."""
    st.subheader("Save to Dashboard")

    project_id = selected_file.project_id

    # Dashboard selection
    dashboards = queries.get_dashboards_for_project(project_id)
    dashboard_options = {d.id: d.name for d in dashboards}
    dashboard_options["__new__"] = "+ Create New Dashboard"

    selected_dash = st.selectbox(
        "Select Dashboard",
        list(dashboard_options.keys()),
        format_func=lambda k: dashboard_options[k],
    )

    dashboard_id = None
    if selected_dash == "__new__":
        # Check dashboard limit
        can_create, limit_msg = credit_service.check_dashboard_limit(ws.id)
        if not can_create:
            st.error(limit_msg)
            return

        new_name = st.text_input("Dashboard Name", placeholder="Sales Dashboard")
        new_desc = st.text_input("Description (optional)")
    else:
        dashboard_id = selected_dash

    # Chart details
    chart_title = st.text_input("Chart Title", value="", placeholder="Revenue by Category")

    if st.button("Save Chart", type="primary", use_container_width=True):
        if selected_dash == "__new__":
            if not new_name:
                st.warning("Please enter a dashboard name.")
                return
            dashboard_id = queries.create_dashboard(
                project_id=project_id,
                created_by=user.id,
                name=new_name,
                description=new_desc or "",
            )

        # Save the chart
        queries.create_chart(
            dashboard_id=dashboard_id,
            file_id=selected_file.id,
            title=chart_title or "Untitled Chart",
            user_prompt=st.session_state.get("wizard_prompt", ""),
            generated_code=st.session_state.get("wizard_code", ""),
            created_by=user.id,
            plotly_json=st.session_state.get("wizard_figure_json"),
        )

        st.success("Chart saved to dashboard!")

        # Reset wizard
        col1, col2 = st.columns(2)
        with col1:
            if st.button("View Dashboard", use_container_width=True):
                st.session_state["view_dashboard_id"] = dashboard_id
                st.switch_page("pages/dashboard_view.py")
        with col2:
            if st.button("Generate Another", use_container_width=True):
                st.session_state["wizard_step"] = 1
                st.session_state.pop("wizard_code", None)
                st.session_state.pop("wizard_figure_json", None)
                st.rerun()


show()
