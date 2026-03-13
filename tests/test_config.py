"""Tests for config helpers."""

import pytest

from github_gaant.config import get_github_token


def test_get_github_token_loads_from_dotenv_in_cwd(tmp_path, monkeypatch):
    """Token should be loaded from .env in current working directory."""
    env_file = tmp_path / ".env"
    env_file.write_text("GITHUB_TOKEN=from_dotenv\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    assert get_github_token() == "from_dotenv"


def test_get_github_token_raises_when_not_set(tmp_path, monkeypatch):
    """Missing token should raise a clear error."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    with pytest.raises(ValueError, match="GITHUB_TOKEN not set"):
        get_github_token()
