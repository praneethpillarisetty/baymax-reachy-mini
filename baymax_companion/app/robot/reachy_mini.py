from __future__ import annotations


class ReachyMiniRobot:
    """Physical adapter intentionally fails closed until the official SDK extra is installed.

    Hardware motion is not claimed as validated. SDK calls are isolated here for a supervised
    integration test rather than emulated or guessed elsewhere.
    """

    def __init__(self):
        raise RuntimeError(
            "Physical Reachy Mini support requires supervised SDK validation; use simulator mode"
        )
