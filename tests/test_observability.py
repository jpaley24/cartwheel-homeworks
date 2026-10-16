"""Authentication tests for the Homework 2 endpoints.

These need no Langfuse, Docker, or model provider key.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from server import app as server_app


def test_session_creation_rejects_role_that_differs_from_database(world: dict) -> None:
    server_app._SESSIONS.clear()
    with pytest.raises(HTTPException) as error:
        server_app.create_session(server_app.SessionCreate(user_id=1, role="support"))
    assert error.value.status_code == 403
    assert server_app._SESSIONS == {}  # nothing was stored


def test_token_for_one_session_cannot_authorize_another(world: dict) -> None:
    server_app._SESSIONS.clear()
    first = server_app.create_session(server_app.SessionCreate(user_id=1, role="shopper"))
    second = server_app.create_session(server_app.SessionCreate(user_id=9002, role="merchant"))
    with pytest.raises(HTTPException) as error:
        server_app._authorize(second["session_id"], f"Bearer {first['token']}")
    assert error.value.status_code == 403
    # the same token still works for its own session
    ctx = server_app._authorize(first["session_id"], f"Bearer {first['token']}")
    assert ctx.user_id == 1
