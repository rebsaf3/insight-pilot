"""REST API routes for AI analysis."""

from fastapi import APIRouter, Depends, HTTPException

from api.auth import get_api_key, get_workspace_from_key, require_permission
from api.schemas import AnalysisRequest, AnalysisResponse
from db import queries
from db.models import ApiKey, Workspace
from services import file_service, llm_service, code_executor, credit_service

router = APIRouter()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    body: AnalysisRequest,
    api_key: ApiKey = Depends(require_permission("analyze")),
    ws: Workspace = Depends(get_workspace_from_key),
):
    """Submit a prompt for AI analysis. Generates a chart and optionally saves to a dashboard."""
    # Verify file exists
    uploaded_file = queries.get_file_by_id(body.file_id)
    if not uploaded_file:
        raise HTTPException(status_code=404, detail="File not found")

    # Check credits
    has_credits, balance = credit_service.check_sufficient_credits(ws.id, 5)
    if not has_credits:
        raise HTTPException(status_code=402, detail=f"Insufficient credits. Balance: {balance}")

    try:
        # Load data
        df = file_service.load_dataframe(uploaded_file.file_path, uploaded_file.file_format)
        profile = uploaded_file.data_profile or {}

        # Generate code
        result = llm_service.generate_chart_code(
            user_prompt=body.prompt,
            data_profile=profile,
            df=df,
        )

        code = result["code"]
        total_tokens = result["tokens_used"]

        # Execute
        exec_result = code_executor.execute_code(code, df)

        # Auto-retry on failure
        retries = 0
        while not exec_result["success"] and retries < 2:
            retries += 1
            refine = llm_service.refine_chart_code(
                original_prompt=body.prompt,
                original_code=code,
                error_message=exec_result["error"],
                data_profile=profile,
                df=df,
            )
            code = refine["code"]
            total_tokens += refine["tokens_used"]
            exec_result = code_executor.execute_code(code, df)

        # Deduct credits
        credit_cost = credit_service.calculate_credit_cost(total_tokens)
        credit_service.deduct_credits(
            workspace_id=ws.id,
            user_id=api_key.created_by,
            amount=credit_cost,
            reason="API analysis",
        )

        # Save prompt history
        queries.save_prompt_history(
            user_id=api_key.created_by,
            workspace_id=ws.id,
            project_id=uploaded_file.project_id,
            file_id=uploaded_file.id,
            prompt_text=body.prompt,
            response_code=code,
            response_error=exec_result.get("error"),
            tokens_used=total_tokens,
            model_used=result["model"],
        )

        if not exec_result["success"]:
            return AnalysisResponse(
                success=False,
                credits_used=credit_cost,
                error=exec_result["error"],
            )

        # Optionally save to dashboard
        chart_id = None
        if body.dashboard_id:
            chart_id = queries.create_chart(
                dashboard_id=body.dashboard_id,
                file_id=uploaded_file.id,
                title=body.chart_title or "API-generated Chart",
                user_prompt=body.prompt,
                generated_code=code,
                created_by=api_key.created_by,
                plotly_json=exec_result["figure"].to_json(),
            )

        return AnalysisResponse(
            success=True,
            chart_id=chart_id,
            explanation=result.get("explanation", ""),
            credits_used=credit_cost,
        )

    except Exception as e:
        return AnalysisResponse(success=False, error=str(e))
