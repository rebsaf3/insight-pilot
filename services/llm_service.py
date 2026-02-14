"""Anthropic Claude API integration — prompt construction, code generation, error recovery."""

import re
from typing import Optional

import anthropic
import pandas as pd

from config.settings import ANTHROPIC_API_KEY, DEFAULT_MODEL, MAX_TOKENS
from prompts.prompt_builder import build_system_prompt, build_messages
from services.data_profiler import profile_to_text_summary


def get_client(api_key: str = None) -> anthropic.Anthropic:
    """Return an Anthropic client."""
    key = api_key or ANTHROPIC_API_KEY
    if not key:
        raise ValueError("No Anthropic API key configured. Set ANTHROPIC_API_KEY in .env or provide your own in Settings.")
    return anthropic.Anthropic(api_key=key)


def generate_chart_code(
    user_prompt: str,
    data_profile: dict,
    df: pd.DataFrame,
    conversation_history: list[dict] = None,
    api_key: str = None,
) -> dict:
    """Send a prompt to Claude to generate plotly visualization code.

    Returns {
        'code': str,
        'explanation': str,
        'tokens_used': int,
        'model': str,
    }
    """
    client = get_client(api_key)

    profile_text = profile_to_text_summary(data_profile)
    column_names = list(df.columns)
    sample_markdown = df.head(5).to_markdown(index=False)

    messages = build_messages(
        user_prompt=user_prompt,
        data_profile_text=profile_text,
        column_names=column_names,
        sample_rows_markdown=sample_markdown,
        conversation_history=conversation_history,
    )

    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=MAX_TOKENS,
        system=build_system_prompt(),
        messages=messages,
        temperature=0.0,
    )

    response_text = response.content[0].text
    code = extract_code_from_response(response_text)
    explanation = extract_explanation_from_response(response_text)

    tokens_used = response.usage.input_tokens + response.usage.output_tokens

    return {
        "code": code,
        "explanation": explanation,
        "tokens_used": tokens_used,
        "model": DEFAULT_MODEL,
    }


def refine_chart_code(
    original_prompt: str,
    original_code: str,
    error_message: str,
    data_profile: dict,
    df: pd.DataFrame,
    api_key: str = None,
) -> dict:
    """Send error context back to Claude for self-correction."""
    client = get_client(api_key)

    profile_text = profile_to_text_summary(data_profile)
    column_names = list(df.columns)
    sample_markdown = df.head(5).to_markdown(index=False)

    messages = build_messages(
        user_prompt=original_prompt,
        data_profile_text=profile_text,
        column_names=column_names,
        sample_rows_markdown=sample_markdown,
        refinement_error=error_message,
        previous_code=original_code,
    )

    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=MAX_TOKENS,
        system=build_system_prompt(),
        messages=messages,
        temperature=0.0,
    )

    response_text = response.content[0].text
    code = extract_code_from_response(response_text)
    explanation = extract_explanation_from_response(response_text)

    tokens_used = response.usage.input_tokens + response.usage.output_tokens

    return {
        "code": code,
        "explanation": explanation,
        "tokens_used": tokens_used,
        "model": DEFAULT_MODEL,
    }


def extract_code_from_response(response_text: str) -> str:
    """Extract Python code from Claude's response."""
    # Try ```python ... ``` blocks first
    pattern = r"```python\s*\n(.*?)```"
    matches = re.findall(pattern, response_text, re.DOTALL)
    if matches:
        return matches[0].strip()

    # Try ``` ... ``` blocks
    pattern = r"```\s*\n(.*?)```"
    matches = re.findall(pattern, response_text, re.DOTALL)
    if matches:
        return matches[0].strip()

    # Fallback: treat entire response as code if it contains 'fig'
    if "fig" in response_text and "import" not in response_text.split("\n")[0]:
        return response_text.strip()

    return response_text.strip()


def extract_explanation_from_response(response_text: str) -> str:
    """Extract the explanation text (non-code part) from the response."""
    # Remove code blocks
    cleaned = re.sub(r"```(?:python)?\s*\n.*?```", "", response_text, flags=re.DOTALL)
    return cleaned.strip()
