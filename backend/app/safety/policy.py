"""Deterministic assistant boundaries, independent from model output."""


import re


def _normalise(message: str) -> str:
    """Keep the safety boundary deliberately small, but insensitive to formatting."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", message.lower()).split())


def safety_response(message: str) -> str | None:
    lowered = _normalise(message)
    # These are clear requests to alter prescribed medication, not a broad
    # attempt at medical-language classification.
    dose_patterns = (
        r"\b(extra|another|more)\s+(metformin|insulin)\b",
        r"\b(double|increase|decrease|change)\s+(my\s+)?(dose|dosage|metformin|insulin)\b",
        r"\btake\s+(an?\s+)?(extra|another)\s+(metformin|insulin|tablet)\b",
        r"\binsulin\s+(dose|correction)\b",
        r"\bhow much\s+(?:.*\s+)?insulin\b",
    )
    if any(re.search(pattern, lowered) for pattern in dose_patterns):
        return "Sugar Path cannot recommend changing a medicine or insulin dose. Please discuss any dose change with your qualified clinician and follow your documented care plan."
    return None
