"""Deterministic assistant boundaries, independent from model output."""


def safety_response(message: str) -> str | None:
    lowered = message.lower()
    dose_terms = (
        "increase my metformin", "decrease my metformin", "extra metformin", "take more metformin",
        "change my dose", "change my dosage", "insulin dose", "insulin correction",
    )
    if any(term in lowered for term in dose_terms):
        return "Sugar Path cannot recommend changing a medicine or insulin dose. Please discuss any dose change with your qualified clinician and follow your documented care plan."
    return None
