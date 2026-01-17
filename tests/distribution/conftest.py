"""
Distribution test fixtures.
"""
from __future__ import annotations

import os
import shutil

import pytest


@pytest.fixture
def no_template_bypass(monkeypatch) -> dict[str, str]:
    """Return environment without SPEC_KITTY_TEMPLATE_ROOT overrides."""
    env = os.environ.copy()

    # Remove all SPEC_KITTY_* overrides except API keys.
    for key in list(env.keys()):
        if key.startswith("SPEC_KITTY_") and key != "SPEC_KITTY_API_KEY":
            env.pop(key, None)

    for key in list(os.environ.keys()):
        if key.startswith("SPEC_KITTY_") and key != "SPEC_KITTY_API_KEY":
            monkeypatch.delenv(key, raising=False)

    return env


@pytest.fixture
def require_jj() -> None:
    """Skip tests when jj is not installed."""
    if shutil.which("jj") is None:
        pytest.skip("jj not installed")
