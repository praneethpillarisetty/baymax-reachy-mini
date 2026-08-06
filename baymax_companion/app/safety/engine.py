from __future__ import annotations

import re

from ..contracts import ModelResponse


class SafetyEngine:
    _patterns = (
        r"(can't|cannot|difficulty|trouble|hard time) breath(e|ing)",
        r"chest pain",
        r"(face droop|slurred speech|sudden weakness|stroke)",
        r"severe bleeding|won't stop bleeding",
        r"overdos(e|ed)|took too many",
        r"unconscious|won't wake",
        r"anaphyla|severe allergic",
        r"suicid|kill myself|self[- ]harm|hurt myself",
    )
    emergency_message = (
        "This may be an emergency. Call your local emergency services now, or ask someone nearby "
        "to call. Do not rely on me for urgent medical care. If you can, move to a safe place and "
        "stay with another person."
    )

    def check(self, text: str) -> ModelResponse | None:
        if any(re.search(pattern, text, re.I) for pattern in self._patterns):
            return ModelResponse(self.emergency_message, emotion="concern")
        return None
