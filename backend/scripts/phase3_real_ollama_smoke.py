"""Manual local verification for Sugar Path's real Ollama integration."""
import json
import os
import urllib.request


QUESTIONS = [
    "Did I take my morning medicine?",
    "How much did I walk yesterday?",
    "What did I eat before my highest glucose today?",
    "Why did my glucose rise this morning?",
    "Should I take extra Metformin because my glucose is high?",
]


def ask(question: str) -> dict:
    request = urllib.request.Request(
        "http://127.0.0.1:8000/api/assistant/chat",
        data=json.dumps({"message": question}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode())


filter_text = os.getenv("PHASE3_SMOKE_FILTER", "").lower()
questions = [question for question in QUESTIONS if not filter_text or filter_text in question.lower()]

for question in questions:
    print(json.dumps({"question": question, "response": ask(question)}), flush=True)
