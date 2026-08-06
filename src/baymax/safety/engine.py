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
    _prohibited_advice = (
        r"\b(i diagnose|you (definitely|certainly) have|this confirms)\b",
        r"\b(stop|start|increase|decrease|double|halve|change) (your )?(dose|dosage|medication)\b",
        r"\b(i prescribe|you are medically cleared|medical clearance)\b",
    )
    limitation_message = (
        "I cannot diagnose, prescribe, change medication dosage, or provide medical clearance. "
        "Please consult a qualified health professional."
    )

    def check(self, text: str) -> ModelResponse | None:
        if any(re.search(pattern, text, re.I) for pattern in self._patterns):
            return ModelResponse(self.emergency_message, emotion="concern")
        return None

    def enforce_output(self, response: ModelResponse) -> ModelResponse:
        if any(re.search(pattern, response.message, re.I) for pattern in self._prohibited_advice):
            return ModelResponse(self.limitation_message, emotion="concern")
        return response

    @classmethod
    def configuration(cls) -> dict[str, object]:
        return {
            "schema": 1,
            "emergency_patterns": list(cls._patterns),
            "prohibited_advice_patterns": list(cls._prohibited_advice),
            "emergency_message": cls.emergency_message,
            "limitation_message": cls.limitation_message,
        }
