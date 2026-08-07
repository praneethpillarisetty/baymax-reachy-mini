from __future__ import annotations

from .contracts import ModelResponse


class ConversationOrchestrator:
    def __init__(self, model, safety, tools, robot, tts, system_prompt: str, fallback_model=None):
        self.model, self.fallback_model, self.safety = model, fallback_model, safety
        self.tools, self.robot, self.tts, self.system_prompt = tools, robot, tts, system_prompt

    def handle(self, text: str) -> ModelResponse:
        response = self.safety.check(text)
        if response is None:
            try:
                response = self.model.generate(text, self.system_prompt)
            except Exception:  # noqa: BLE001: model backends may raise diverse runtime errors; fallback must catch all
                if self.fallback_model is not None:
                    try:
                        response = self.fallback_model.generate(text, self.system_prompt)
                    except Exception:  # noqa: BLE001: allow fallback to absorb any model errors
                        response = self._failure()
                else:
                    response = self._failure()
        response = self.safety.enforce_output(response)
        results = []
        for action in response.actions:
            try:
                results.append(self.tools.execute(action))
            except Exception as exc:  # noqa: BLE001: tools are 3rd-party; surface failures rather than crashing
                results.append(f"Action failed: {exc}")
        if results:
            response = ModelResponse(
                response.message + "\n" + "\n".join(results), emotion=response.emotion
            )
        self.robot.express(response.emotion)
        self.tts.speak(response.message)
        return response

    @staticmethod
    def _failure() -> ModelResponse:
        return ModelResponse(
            "I am having trouble with my local conversation model. Reminders and emergency guidance remain available.",
            emotion="concern",
        )
