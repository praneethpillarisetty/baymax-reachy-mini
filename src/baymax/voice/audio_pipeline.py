from __future__ import annotations

import threading


class AudioPipeline:
    def __init__(self, asr, tts):
        self.asr, self.tts = asr, tts
        self.cancelled = threading.Event()

    def receive(self) -> str:
        if self.cancelled.is_set():
            raise RuntimeError("audio input cancelled")
        try:
            return self.asr.listen()
        except Exception as exc:
            raise RuntimeError("audio input failed") from exc

    def send(self, text: str) -> None:
        if self.cancelled.is_set():
            return
        try:
            self.tts.speak(text)
        except Exception as exc:
            raise RuntimeError("audio output failed") from exc

    def cancel(self) -> None:
        self.cancelled.set()
        for adapter in (self.asr, self.tts):
            cancel = getattr(adapter, "cancel", None)
            if callable(cancel):
                cancel()

    def shutdown(self) -> None:
        self.cancel()
