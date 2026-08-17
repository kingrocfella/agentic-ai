"""Regression tests for P0 security controls."""

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.config import _required_setting
from app.main import not_found_handler
from app.utils.logger import sanitize_log_text


def test_404_is_bounded_first_party_json():
    """Unknown paths must not redirect users to an external large download."""
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/missing",
            "headers": [],
            "query_string": b"",
            "server": ("test", 80),
            "client": ("test", 1234),
            "scheme": "http",
        }
    )

    response = not_found_handler(request, HTTPException(status_code=404))

    assert response.status_code == 404
    assert response.headers.get("location") is None
    assert response.body == b'{"detail":"Not found"}'


def test_required_settings_reject_missing_and_placeholder_values(monkeypatch):
    """Production configuration must fail closed instead of casting None."""
    monkeypatch.delenv("P0_TEST_SECRET", raising=False)
    with pytest.raises(RuntimeError):
        _required_setting("P0_TEST_SECRET", 32)

    monkeypatch.setenv("P0_TEST_SECRET", "change-me-to-something-longer-than-32-chars")
    with pytest.raises(RuntimeError):
        _required_setting("P0_TEST_SECRET", 32)


def test_log_sink_redacts_credentials_and_email_addresses():
    rendered = sanitize_log_text(
        "user@example.com Bearer abc.def.ghi https://app/reset?token=secret"
    )
    assert "user@example.com" not in rendered
    assert "abc.def.ghi" not in rendered
    assert "token=secret" not in rendered
