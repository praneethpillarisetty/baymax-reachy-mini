from ..contracts import ModelResponse


class MockModel:
    def generate(self, text: str, system_prompt: str) -> ModelResponse:
        return ModelResponse(f"I hear you. You said: {text}", emotion="caring")
