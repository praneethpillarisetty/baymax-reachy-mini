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
        if response is None:
            try:
                response = self.model.generate(text, self.system_prompt)
            except Exception:  # noqa: BLE001 -- model adapters have diverse optional runtime errors
                if self.fallback_model is not None:
                    try:
                        response = self.fallback_model.generate(text, self.system_prompt)
                    except Exception:  # noqa: BLE001 -- fallback adapters also have optional runtimes
                        response = self._failure()
                else:
                    response = self._failure()
        if not isinstance(response, ModelResponse):
            response = parse_model_response(response)
        response = self.safety.enforce_output(response)
        results = []
        for action in response.actions:
            try:
                results.append(self.tools.execute(action))
            except Exception as exc:  # noqa: BLE001 -- surface allow-listed tool failures
                results.append(f"Action failed: {exc}")
        if results:
            response = ModelResponse(
                response.message + "\n" + "\n".join(results), emotion=response.emotion
            )
        try:
            self.robot.express(response.emotion)
        except (RuntimeError, OSError):
            pass
        try:
            self.tts.speak(response.message)
        except (RuntimeError, OSError):
            pass  # Text response remains available when local voice fails.
        return response

    def safe_stop(self) -> None:
        """Stop/cancel output before any lower-priority expression work."""
        self.robot.stop_motion()
        for model in (self.model, self.fallback_model):
            cancel = getattr(model, "cancel", None)
            if callable(cancel):
                cancel()

    @staticmethod
    def _failure() -> ModelResponse:
        return ModelResponse(
            "I am having trouble with my local conversation model. Reminders and emergency guidance remain available.",
            emotion="concern",
        )
