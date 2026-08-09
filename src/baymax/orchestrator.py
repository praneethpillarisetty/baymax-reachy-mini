from __future__ import annotations

from .contracts import ModelResponse
from .models.base import parse_model_response

MAX_MESSAGE_CHARS = 4000


class ConversationOrchestrator:
    def __init__(self, model, safety, tools, robot, tts, system_prompt: str, fallback_model=None):
        self.model, self.fallback_model, self.safety = model, fallback_model, safety
        self.tools, self.robot, self.tts, self.system_prompt = tools, robot, tts, system_prompt

    def handle(self, text: str) -> ModelResponse:
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_MESSAGE_CHARS:
            raise ValueError("message must contain 1-4000 characters")
        response = self.safety.check(text)
        emergency = response is not None
        backend = "safety" if emergency else self._backend_name(self.model)
        fallback_reason = None
        if response is None:
            try:
                response = self.model.generate(text, self.system_prompt)
            except Exception as exc:  # noqa: BLE001 -- adapters have diverse optional errors
                fallback_reason = self._safe_failure_reason(exc)
                if self.fallback_model is not None:
                    try:
                        response = self.fallback_model.generate(text, self.system_prompt)
                        backend = self._backend_name(self.fallback_model)
                    except Exception:  # noqa: BLE001 -- fallback adapters also have optional runtimes
                        response = self._failure()
                        backend = "failure"
                else:
                    response = self._failure()
                    backend = "failure"
        if not isinstance(response, ModelResponse):
            response = parse_model_response(response)
        response = self.safety.enforce_output(response)
        response = ModelResponse(
            response.message,
            response.actions,
            response.emotion,
            backend,
            fallback_reason,
        )
        results = []
        for action in response.actions:
            try:
                results.append(self.tools.execute(action))
            except Exception as exc:  # noqa: BLE001 -- surface allow-listed tool failures
                results.append(f"Action failed: {exc}")
        if results:
            response = ModelResponse(
                response.message + "\n" + "\n".join(results),
                emotion=response.emotion,
                backend=response.backend,
                fallback_reason=response.fallback_reason,
            )
        # Emergency guidance must never cause physical movement. Text/audio remains available.
        if not emergency:
            try:
                self.robot.express(response.emotion)
            except (RuntimeError, OSError):
                pass
        try:
            self.tts.speak(response.message)
        except (RuntimeError, OSError):
            pass  # Text response remains available when local voice fails.
        return response

    @staticmethod
    def _backend_name(model) -> str:
        return str(getattr(model, "backend_name", model.__class__.__name__.removesuffix("Model"))).lower()

    @staticmethod
    def _safe_failure_reason(exc: Exception) -> str:
        """Return bounded adapter diagnostics without prompts, payloads, or chained exceptions."""
        detail = " ".join(str(exc).split())
        return (detail or f"{type(exc).__name__} while generating")[:200]

    def safe_stop(self) -> None:
        """Stop/cancel output before any lower-priority expression work."""
        self.robot.stop_motion()
        for model in (self.model, self.fallback_model):
            cancel = getattr(model, "cancel", None)
            if callable(cancel):
                cancel()
        cancel_tts = getattr(self.tts, "cancel", None)
        if callable(cancel_tts):
            cancel_tts()

    @staticmethod
    def _failure() -> ModelResponse:
        return ModelResponse(
            "I am having trouble with my local conversation model. Reminders and emergency guidance remain available.",
            emotion="concern",
        )
