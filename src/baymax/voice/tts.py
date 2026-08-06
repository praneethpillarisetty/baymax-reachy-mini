class ConsoleTTS:
    def speak(self, text: str) -> None:
        print(f"Companion: {text}")


class MockTTS:
    def __init__(self):
        self.spoken: list[str] = []

    def speak(self, text: str) -> None:
        self.spoken.append(text)
