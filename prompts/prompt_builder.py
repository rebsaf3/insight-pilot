"""Assembles full prompts from data profile, examples, and user query."""

from prompts.system_prompt import SYSTEM_PROMPT
from prompts.few_shot_examples import EXAMPLES


def build_system_prompt(project_instructions: str = None) -> str:
    """Return the system prompt, optionally with per-project instructions appended."""
    prompt = SYSTEM_PROMPT
    if project_instructions and project_instructions.strip():
        prompt += f"""

PROJECT-SPECIFIC INSTRUCTIONS (always follow these for every chart you generate):
{project_instructions.strip()}
"""
    return prompt


def build_messages(
    user_prompt: str,
    data_profile_text: str,
    column_names: list[str],
    sample_rows_markdown: str,
    conversation_history: list[dict] = None,
    refinement_error: str = None,
    previous_code: str = None,
) -> list[dict]:
    """Build the messages array for the Anthropic API.

    Returns a list of {"role": ..., "content": ...} dicts.
    """
    messages = []

    # Data context message
    data_context = f"""Here is the dataset you will work with:

DATASET PROFILE:
{data_profile_text}

COLUMN NAMES: {', '.join(column_names)}

SAMPLE DATA (first 5 rows):
{sample_rows_markdown}

Remember: the data is already loaded as `df`. Create a plotly figure assigned to `fig`."""

    messages.append({"role": "user", "content": data_context})
    messages.append({
        "role": "assistant",
        "content": f"I understand the dataset with {len(column_names)} columns. I'm ready to generate visualizations. What would you like to see?",
    })

    # Few-shot examples
    for example in EXAMPLES:
        messages.append({
            "role": "user",
            "content": f"Data profile:\n{example['profile_summary']}\n\nRequest: {example['user_prompt']}",
        })
        messages.append({
            "role": "assistant",
            "content": f"```python\n{example['code']}\n```",
        })

    # Conversation history (for multi-turn refinement)
    if conversation_history:
        for msg in conversation_history:
            messages.append(msg)

    # Error refinement context
    if refinement_error and previous_code:
        messages.append({
            "role": "user",
            "content": f"""The following code failed with an error. Please fix it.

PREVIOUS CODE:
```python
{previous_code}
```

ERROR:
{refinement_error}

Please return only the corrected Python code.""",
        })
    else:
        messages.append({"role": "user", "content": user_prompt})

    return messages
