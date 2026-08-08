from ..contracts import ModelResponse


class MockModel:
    def health_check(self) -> tuple[bool, str]:
        return True, "built-in deterministic mock model"

    def cancel(self) -> None:
        return

    def generate(self, text: str, system_prompt: str) -> ModelResponse:
        return ModelResponse(f"I hear you. You said: {text}", emotion="caring")
