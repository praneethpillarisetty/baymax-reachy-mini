from __future__ import annotations

import os

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if os.getenv("BAYMAX_PHYSICAL_TESTS") == "1":
        return
    skip = pytest.mark.skip(reason="requires BAYMAX_PHYSICAL_TESTS=1 and supervised hardware")
    for item in items:
        if "physical" in item.keywords:
            item.add_marker(skip)
