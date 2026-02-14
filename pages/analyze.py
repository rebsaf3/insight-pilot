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
    successful_files = [f for f in files if getattr(f, "status", "success") == "success"]

    # Show landing page if wizard hasn't been started yet
    if not st.session_state.get("analyze_wizard_active"):
        _show_landing(user, ws, project, successful_files)
        return

    # ---- Wizard mode ----
    # Store project instructions for use in generation
    st.session_state["project_instructions"] = project.instructions or ""

    # Show active project instructions banner
    if project.instructions:
        with st.expander("Active Project Instructions", expanded=False, icon=":material/description:"):
            st.info(project.instructions)

    if not successful_files:
        st.warning("No successfully imported data files in this project. Upload data first.")
        st.stop()

    # File selector
    file_names = {f.id: f.original_filename for f in successful_files}
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
            col.markdown(f"<span style='color:#9CA3AF'>{label}</span>", unsafe_allow_html=True)

    st.divider()

    if step == 1:
        _step_describe(user, ws, selected_file)
    elif step == 2:
        _step_review(user, ws, selected_file)
    elif step == 3:
        _step_save(user, ws, selected_file)


def _show_landing(user, ws, project, files):
    """Show the analyze landing page with project context and quick actions."""
    # Project context card
    st.markdown(
        f"<div class='ip-card' style='margin-bottom:1.5rem'>"
        f"<div style='display:flex;align-items:center;gap:0.75rem'>"
        f"<span class='material-symbols-rounded' style='font-size:1.75rem;color:#0F766E'>folder</span>"
        f"<div>"
        f"<div style='font-weight:700;font-size:1rem'>{project.name}</div>"
        f"<div style='font-size:0.82rem;color:#57534E'>"
        f"{project.description or 'No description'}</div>"
        f"</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    if not files:
        st.warning("No data files in this project. Upload data first.")
        return

    # Quick action cards
    st.markdown("<div class='ip-section-header'><h3>Quick Actions</h3></div>", unsafe_allow_html=True)
    actions = [
        ("trending_up", "Trend Analysis", "Track patterns over time"),
        ("bar_chart", "Comparison", "Compare categories and groups"),
        ("summarize", "Summary", "Get a data overview"),
        ("edit", "Custom Prompt", "Describe exactly what you need"),
    ]
    action_cols = st.columns(len(actions))
    for col, (icon, title, desc) in zip(action_cols, actions):
        with col:
            st.markdown(
                f"<div class='ip-action-card'>"
                f"<div class='icon'><span class='material-symbols-rounded'>{icon}</span></div>"
                f"<div class='title'>{title}</div>"
                f"<div class='desc'>{desc}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # Start new analysis button
    st.markdown("")
    if st.button("Start New Analysis", type="primary", use_container_width=True, icon=":material/analytics:"):
        st.session_state["analyze_wizard_active"] = True
        st.session_state["wizard_step"] = 1
        st.rerun()

    # Recent analyses
    recent = queries.get_prompt_history(ws.id, project.id, limit=5)
    if recent:
        st.markdown("<div class='ip-section-header' style='margin-top:1.5rem'><h3>Recent Analyses</h3></div>", unsafe_allow_html=True)
        for entry in recent:
            prompt_preview = entry.prompt_text[:100] + ("..." if len(entry.prompt_text) > 100 else "")
            status_cls = "ip-badge-success" if not entry.response_error else "ip-badge-error"
            status_label = "Success" if not entry.response_error else "Error"
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:0.75rem;padding:0.5rem 0;"
                f"border-bottom:1px solid #F5F5F4;font-family:Inter,sans-serif'>"
                f"<div style='flex:1;font-size:0.85rem'>{prompt_preview}</div>"
                f"<div style='font-size:0.72rem;color:#A8A29E'>{entry.tokens_used} tokens</div>"
                f"<span class='ip-badge {status_cls}'>{status_label}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )


def _step_describe(user, ws, selected_file):
    """Step 1: Describe what you want."""
    # Show data profile summary
    if selected_file.data_profile:
        profile_text = data_profiler.profile_to_text_summary(selected_file.data_profile)
        with st.expander("Data Profile", expanded=False):
            st.code(profile_text)

    # Credit check
    has_credits, balance = credit_service.check_sufficient_credits(ws.id, 5)

    # Prompt Templates
    templates = queries.get_prompt_templates_for_project(selected_file.project_id)
    if templates:
        template_options = {"": "-- Write your own --"}
        template_options.update({t.id: t.name for t in templates})
        selected_template_id = st.selectbox(
            "Use a saved template",
            list(template_options.keys()),
            format_func=lambda k: template_options[k],
            key="template_selector",
        )
        if selected_template_id:
            template = queries.get_prompt_template_by_id(selected_template_id)
            if template:
                st.session_state["wizard_prompt_input"] = template.prompt_text

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

    # Save as template
    with st.expander("Save as Template", expanded=False):
        tmpl_name = st.text_input("Template name", key="save_tmpl_name")
        if st.button("Save Template", disabled=not (prompt and tmpl_name)):
            queries.create_prompt_template(
                project_id=selected_file.project_id,
                created_by=user.id,
                name=tmpl_name,
                prompt_text=prompt,
            )
            st.success(f"Template '{tmpl_name}' saved!")
            st.rerun()

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

        # Increment template usage if one was selected
        tmpl_id = st.session_state.get("template_selector", "")
        if tmpl_id:
            queries.increment_template_usage(tmpl_id)

        _generate_chart(user, ws, selected_file, prompt)


def _generate_chart(user, ws, selected_file, prompt, is_revision=False):
    """Generate a chart from the prompt."""
    project_instructions = st.session_state.get("project_instructions", "")

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
                project_instructions=project_instructions,
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
                    project_instructions=project_instructions,
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
