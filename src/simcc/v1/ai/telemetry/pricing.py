from typing import Dict

# Preços aproximados em USD por 1M de tokens (OpenAI)
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    'gpt-4o-mini': {
        'input_per_million': 0.15,
        'output_per_million': 0.60,
    },
    'gpt-4o': {
        'input_per_million': 2.50,
        'output_per_million': 10.00,
    },
    'text-embedding-3-small': {
        'input_per_million': 0.02,
        'output_per_million': 0.0,
    },
}


def estimate_tokens(text: str) -> int:
    """
    Estimativa rápida e determinística de contagem de tokens baseada em caracteres/palavras.
    Aproximação: ~4 caracteres por token em português/código.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


def calculate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int = 0,
) -> float:
    pricing = MODEL_PRICING.get(model, MODEL_PRICING['gpt-4o-mini'])
    input_cost = (prompt_tokens / 1_000_000) * pricing['input_per_million']
    output_cost = (completion_tokens / 1_000_000) * pricing[
        'output_per_million'
    ]
    return round(input_cost + output_cost, 6)
