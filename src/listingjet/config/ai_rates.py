"""USD rates. Token rates are per 1M tokens (input, output); image rates per call.
Source: Anthropic price list cached 2026-06 in the claude-api skill; OpenAI image pricing
as observed in openai_dollhouse.py. Update here, nowhere else."""

TOKEN_RATES: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-5": (5.00, 25.00),
}

IMAGE_CALL_RATES: dict[str, float] = {
    "gpt-image-1.5": 0.05,   # 1536x1024 medium
}

LEGACY_CALL_RATES: dict[str, float] = {  # until Task 4 removes Kling entirely
    "kling": 0.50,
}

VIDEO_SECOND_RATES: dict[str, float] = {  # USD per generated second, Runway two-tier
    "gen4_turbo": 0.05,
    "veo3.1_fast": 0.10,
}
