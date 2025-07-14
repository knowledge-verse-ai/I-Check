from typing import Dict, Any, Tuple

REQUIRED_PARAMS = {
    "faq_generator": ["question_count", "model_name"],
    "summariser": ["compression_ratio", "model_name"],
    "k_search": ["sources", "query_text", "model_name"],
    "doc_extractor": ["entity_list", "model_name"],
}

OPTIONAL_PARAMS = {
    "faq_generator": ["focus_areas"],
    "summariser": ["focus_areas"],
    "k_search": [],
    "doc_extractor": [],
}

def process_agent_params(agent: str, params: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], list]:
    """
    Validates agent-specific parameters.
    Returns: (is_valid, cleaned_params, missing_keys)
    """
    agent = agent.lower()

    if agent not in REQUIRED_PARAMS:
        raise ValueError(f"Unknown agent: {agent}")

    required = REQUIRED_PARAMS[agent]
    optional = OPTIONAL_PARAMS[agent]
    allowed_keys = set(required + optional)

    # Identify missing required keys
    missing_keys = [key for key in required if key not in params]

    # Filter to allowed keys only (ignore extras)
    cleaned_params = {k: v for k, v in params.items() if k in allowed_keys}

    return (len(missing_keys) == 0, cleaned_params, missing_keys)

def get_standard_model_name(model_name: str) -> str:
    """
    Standardises model names to a common format.
    """
    model_name = model_name.lower().replace(" ", "_")
    if model_name.lower().startswith("gpt") and not(model_name.lower().endswith("mini")):
        return "gpt-4o"
    elif model_name.lower().startswith("gpt") and model_name.lower().endswith("mini"):
        return "gpt-4o-mini"
    elif model_name.lower().startswith("claude"):
        return "claude-sonnet-4"
    elif model_name.lower().startswith("gemini"):
        return "gemini-2.5-flash"
    elif model_name.lower().startswith("mistral"):
        return "mistral-large"
    else:
        return "gpt-4o"  # Default fallback