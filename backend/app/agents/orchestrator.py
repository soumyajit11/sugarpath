import json
import logging
from time import perf_counter
from sqlalchemy.orm import Session

from app.agents.prompts import SYSTEM_PROMPT
from app.agents.tools import REGISTRY, TOOL_MAP
from app.config import settings
from app.safety import safety_response
from app.services.ollama_service import OllamaClient, OllamaError, OllamaUnavailable

logger = logging.getLogger(__name__)


class SugarPathAgent:
    def __init__(self, client: OllamaClient | None = None, max_iterations: int | None = None):
        self.client = client or OllamaClient()
        self.max_iterations = max_iterations or settings.max_tool_iterations

    def respond(self, db: Session, user_message: str) -> dict:
        boundary = safety_response(user_message)
        if boundary:
            return {"message": boundary, "sources_used": [], "status": "safe_boundary"}
        started = perf_counter(); sources: list[str] = []
        messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_message}]
        executed_tools: set[str] = set()
        lowered = user_message.lower()
        required_tools = {"get_meal_before_highest_glucose"} if "highest glucose" in lowered and "eat" in lowered else set()
        if any(phrase in lowered for phrase in ("what do you remember", "remember about me", "usually", "preference")):
            required_tools = {"get_agent_memories"}
        if "remember" in lowered and any(phrase in lowered for phrase in ("remember that", "remember my", "please remember")):
            required_tools = {"store_agent_memory"}
        if "why" in lowered and "glucose" in lowered and ("rise" in lowered or "rising" in lowered):
            required_tools = {"get_morning_glucose_context"}
        try:
            for iteration in range(self.max_iterations):
                logger.info("agent_invocation iteration=%d", iteration + 1)
                answer = self.client.chat(messages, [tool.ollama_definition() for tool in REGISTRY])
                calls = answer.get("tool_calls") or []
                if not calls:
                    content = answer.get("content")
                    if not isinstance(content, str) or not content.strip():
                        raise OllamaError("Model response contained no answer")
                    if content.lstrip().startswith(("{\"name\"", "{\"function\"", "function_call")):
                        raise OllamaError("Model returned a malformed tool request")
                    missing = required_tools - executed_tools
                    if missing:
                        messages.append({"role": "user", "content": f"Before answering, call these required native tools: {', '.join(sorted(missing))}. Do not answer until you have their results."})
                        continue
                    logger.info("agent_completed latency_ms=%d", (perf_counter() - started) * 1000)
                    return {"message": content.strip(), "sources_used": sources, "status": "ok"}
                messages.append({"role": "assistant", "content": answer.get("content") or "", "tool_calls": calls})
                for call in calls:
                    function = call.get("function", {}) if isinstance(call, dict) else {}
                    name, arguments = function.get("name"), function.get("arguments", {})
                    if isinstance(arguments, str):
                        try: arguments = json.loads(arguments)
                        except ValueError: arguments = {}
                    tool = TOOL_MAP.get(name)
                    if tool is None:
                        result = {"ok": False, "error": "That requested operation is not available."}
                        logger.warning("agent_unknown_tool tool=%s", name)
                    elif not isinstance(arguments, dict):
                        result = {"ok": False, "error": "The requested operation had invalid input."}
                    else:
                        result = tool.execute(db, arguments)
                        if result["ok"]:
                            executed_tools.add(tool.name)
                        if result["ok"] and tool.source not in sources: sources.append(tool.source)
                    messages.append({"role": "tool", "content": json.dumps(result, default=str)})
            logger.warning("agent_max_iterations_reached max=%d", self.max_iterations)
            return {"message": "Sugar Path needs a moment to finish checking your information. Please try again.", "sources_used": sources, "status": "limit_reached"}
        except OllamaUnavailable:
            return {"message": "Sugar Path's AI assistant is temporarily unavailable.", "sources_used": [], "status": "unavailable"}
        except OllamaError:
            logger.warning("agent_model_error")
            return {"message": "Sugar Path's AI assistant is temporarily unavailable.", "sources_used": sources, "status": "unavailable"}
        except Exception:
            logger.exception("agent_failed")
            return {"message": "Sugar Path's AI assistant is temporarily unavailable.", "sources_used": [], "status": "unavailable"}
