import json

import pytest
from starlette.websockets import WebSocketDisconnect


def test_websocket_rejects_missing_token(client, created_sheet):
    sheet_id = created_sheet["id"]
    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/collaborate/{sheet_id}"):
            pass


def test_websocket_rejects_invalid_token(client, created_sheet):
    sheet_id = created_sheet["id"]
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            f"/ws/collaborate/{sheet_id}?token=not-a-real-token"
        ) as ws:
            ws.receive_text()


def test_websocket_rejects_unknown_sheet(client, auth_token):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            f"/ws/collaborate/99999?token={auth_token}"
        ) as ws:
            ws.receive_text()


def test_websocket_connects_and_sends_initial_state(
    client, auth_token, created_sheet
):
    sheet_id = created_sheet["id"]
    with client.websocket_connect(
        f"/ws/collaborate/{sheet_id}?token={auth_token}"
    ) as ws:
        message = json.loads(ws.receive_text())
        assert message["type"] == "connected"
        assert message["sheet_id"] == sheet_id
        assert isinstance(message["active_users"], list)


def test_websocket_rejects_other_users_sheet(
    client, second_user_headers, created_sheet
):
    # second_user_headers fixture also sets a user up; pull token out of the header.
    token = second_user_headers["Authorization"].split(" ", 1)[1]
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            f"/ws/collaborate/{created_sheet['id']}?token={token}"
        ) as ws:
            ws.receive_text()
