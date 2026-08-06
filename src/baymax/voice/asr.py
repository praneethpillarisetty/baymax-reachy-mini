class ConsoleASR:
    def listen(self) -> str:
        return input("You: ").strip()


class MockASR:
    def __init__(self, utterances=()):
        self.utterances = iter(utterances)

    def listen(self) -> str:
        return next(self.utterances)
