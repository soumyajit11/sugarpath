"""Small Ollama HTTP adapter; routes and tools never call the model directly."""
import json
import logging
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import settings

logger = logging.getLogger(__name__)


class OllamaError(RuntimeError):
    pass


class OllamaUnavailable(OllamaError):
    pass


class OllamaClient:
    def chat(self, messages: list[dict], tools: list[dict]) -> dict:
        if not settings.ollama_model:
            raise OllamaUnavailable("No Ollama model is configured")
        payload = json.dumps({"model": settings.ollama_model, "messages": messages, "tools": tools, "stream": False, "options": {"temperature": 0, "num_predict": 180}}).encode()
        request = Request(f"{settings.ollama_base_url.rstrip('/')}/api/chat", data=payload, headers={"Content-Type": "application/json"}, method="POST")
        started = perf_counter()
        try:
            with urlopen(request, timeout=settings.ollama_timeout_seconds) as response:
                result = json.loads(response.read().decode())
        except (URLError, TimeoutError, HTTPError, ValueError) as exc:
            logger.warning("ollama_request_failed error=%s", type(exc).__name__)
            raise OllamaUnavailable("Ollama is unavailable") from exc
        logger.info("ollama_request_completed latency_ms=%d", (perf_counter() - started) * 1000)
        if not isinstance(result.get("message"), dict):
            raise OllamaError("Malformed response from Ollama")
        return result["message"]
