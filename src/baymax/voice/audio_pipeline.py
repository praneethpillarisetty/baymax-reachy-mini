from __future__ import annotations


class AudioPipeline:
    def __init__(self, asr, tts):
        self.asr, self.tts = asr, tts

    def receive(self) -> str:
        try:
            return self.asr.listen()
        except Exception as exc:
            raise RuntimeError("audio input failed") from exc

    def send(self, text: str) -> None:
        try:
            self.tts.speak(text)
        except Exception as exc:
            raise RuntimeError("audio output failed") from exc
