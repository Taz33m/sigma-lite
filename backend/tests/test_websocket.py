import json
from contextlib import ExitStack

import pytest
from starlette.websockets import WebSocketDisconnect

from app.api.routes.websocket import (
    MAX_CONNECTIONS_PER_USER_PER_SHEET,
    MAX_PRESENCE_MESSAGE_BYTES,
    PRESENCE_CLOSE_CODE,
    PRESENCE_RATE_LIMIT,
    presence_rate_limiter,
)
from app.services.websocket_manager import manager


@pytest.fixture(autouse=True)
def reset_websocket_state():
    presence_rate_limiter.reset()
    yield
    presence_rate_limiter.reset()
    manager.active_connections.clear()
    manager.connection_info.clear()


def _receive_json(ws):
    return json.loads(ws.receive_text())


def _ws_ticket(client, headers, sheet_id):
    response = client.post(f"/api/sheets/{sheet_id}/ws-ticket", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["ticket"]


def test_websocket_rejects_missing_ticket(client, created_sheet):
    sheet_id = created_sheet["id"]
    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/collaborate/{sheet_id}"):
            pass


def test_websocket_rejects_invalid_ticket(client, created_sheet):
    sheet_id = created_sheet["id"]
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            f"/ws/collaborate/{sheet_id}?ticket=not-a-real-ticket"
        ) as ws:
            ws.receive_text()


def test_websocket_rejects_unknown_sheet(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            "/ws/collaborate/99999?ticket=not-a-real-ticket"
        ) as ws:
            ws.receive_text()


def test_websocket_connects_and_sends_initial_state(
    client, auth_headers, created_sheet
):
    sheet_id = created_sheet["id"]
    ticket = _ws_ticket(client, auth_headers, sheet_id)
    with client.websocket_connect(
        f"/ws/collaborate/{sheet_id}?ticket={ticket}"
    ) as ws:
        message = _receive_json(ws)
        assert message["type"] == "connected"
        assert message["sheet_id"] == sheet_id
        assert isinstance(message["active_users"], list)


def test_websocket_allows_shared_sheet_user(
    client, auth_headers, second_user_headers, created_sheet
):
    share = client.post(
        f"/api/sheets/{created_sheet['id']}/shares",
        headers=auth_headers,
        json={"username_or_email": "otheruser", "role": "viewer"},
    )
    assert share.status_code == 201, share.text

    ticket = _ws_ticket(client, second_user_headers, created_sheet["id"])
    with client.websocket_connect(
        f"/ws/collaborate/{created_sheet['id']}?ticket={ticket}"
    ) as ws:
        message = _receive_json(ws)
        assert message["type"] == "connected"
        assert message["sheet_id"] == created_sheet["id"]


def test_websocket_broadcasts_valid_presence_messages(
    client, auth_headers, second_user_headers, created_sheet
):
    share = client.post(
        f"/api/sheets/{created_sheet['id']}/shares",
        headers=auth_headers,
        json={"username_or_email": "otheruser", "role": "viewer"},
    )
    assert share.status_code == 201, share.text

    sheet_url = f"/ws/collaborate/{created_sheet['id']}"
    sender_ticket = _ws_ticket(client, auth_headers, created_sheet["id"])
    receiver_ticket = _ws_ticket(client, second_user_headers, created_sheet["id"])

    with client.websocket_connect(f"{sheet_url}?ticket={sender_ticket}") as sender:
        assert _receive_json(sender)["type"] == "connected"

        with client.websocket_connect(
            f"{sheet_url}?ticket={receiver_ticket}"
        ) as receiver:
            assert _receive_json(receiver)["type"] == "connected"
            assert _receive_json(sender)["type"] == "user_joined"

            sender.send_text(
                json.dumps({"type": "cursor", "row": 1, "column": "city"})
            )
            cursor = _receive_json(receiver)
            assert cursor["type"] == "cursor"
            assert cursor["row"] == 1
            assert cursor["column"] == "city"
            assert cursor["username"] == "fixtureuser"

            sender.send_text(
                json.dumps(
                    {
                        "type": "selection",
                        "start_row": 1,
                        "start_column": "city",
                        "end_row": 2,
                        "end_column": "age",
                    }
                )
            )
            selection = _receive_json(receiver)
            assert selection["type"] == "selection"
            assert selection["start_row"] == 1
            assert selection["start_column"] == "city"
            assert selection["end_row"] == 2
            assert selection["end_column"] == "age"


def test_websocket_limits_connections_per_user_per_sheet(
    client, auth_headers, created_sheet
):
    sheet_url = f"/ws/collaborate/{created_sheet['id']}"

    with ExitStack() as stack:
        for _ in range(MAX_CONNECTIONS_PER_USER_PER_SHEET):
            ticket = _ws_ticket(client, auth_headers, created_sheet["id"])
            ws = stack.enter_context(client.websocket_connect(f"{sheet_url}?ticket={ticket}"))
            assert _receive_json(ws)["type"] == "connected"

        blocked_ticket = _ws_ticket(client, auth_headers, created_sheet["id"])
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"{sheet_url}?ticket={blocked_ticket}") as blocked:
                blocked.receive_text()
        assert exc_info.value.code == 1008


def test_websocket_rejects_direct_cell_update_messages(
    client, auth_headers, created_sheet
):
    ticket = _ws_ticket(client, auth_headers, created_sheet["id"])
    with client.websocket_connect(
        f"/ws/collaborate/{created_sheet['id']}?ticket={ticket}"
    ) as ws:
        connected = _receive_json(ws)
        assert connected["type"] == "connected"

        ws.send_text(
            json.dumps(
                {
                    "type": "cell_update",
                    "row": 0,
                    "column": "city",
                    "value": "Boston",
                }
            )
        )
        message = _receive_json(ws)
        assert message["type"] == "cell_update_rejected"
        assert "REST cell endpoint" in message["reason"]


def test_websocket_rejects_direct_comment_messages(
    client, auth_headers, created_sheet
):
    ticket = _ws_ticket(client, auth_headers, created_sheet["id"])
    with client.websocket_connect(
        f"/ws/collaborate/{created_sheet['id']}?ticket={ticket}"
    ) as ws:
        connected = _receive_json(ws)
        assert connected["type"] == "connected"

        ws.send_text(
            json.dumps(
                {
                    "type": "comment",
                    "row_index": 0,
                    "column": "city",
                    "text": "Looks good",
                }
            )
        )
        message = _receive_json(ws)
        assert message["type"] == "comment_rejected"
        assert "REST comment endpoint" in message["reason"]


def test_websocket_rejects_oversized_presence_payload(
    client, auth_headers, created_sheet
):
    ticket = _ws_ticket(client, auth_headers, created_sheet["id"])
    with client.websocket_connect(
        f"/ws/collaborate/{created_sheet['id']}?ticket={ticket}"
    ) as ws:
        assert _receive_json(ws)["type"] == "connected"

        oversized = json.dumps(
            {
                "type": "cursor",
                "row": 0,
                "column": "city",
                "padding": "x" * MAX_PRESENCE_MESSAGE_BYTES,
            }
        )
        ws.send_text(oversized)

        message = _receive_json(ws)
        assert message["type"] == "error"
        assert message["code"] == "payload_too_large"

        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_text()
        assert exc_info.value.code == PRESENCE_CLOSE_CODE


def test_websocket_rate_limits_presence_fanout(
    client, auth_headers, created_sheet
):
    ticket = _ws_ticket(client, auth_headers, created_sheet["id"])
    with client.websocket_connect(
        f"/ws/collaborate/{created_sheet['id']}?ticket={ticket}"
    ) as ws:
        assert _receive_json(ws)["type"] == "connected"

        for row in range(PRESENCE_RATE_LIMIT):
            ws.send_text(
                json.dumps({"type": "cursor", "row": row, "column": "city"})
            )

        ws.send_text(
            json.dumps(
                {"type": "cursor", "row": PRESENCE_RATE_LIMIT, "column": "city"}
            )
        )

        message = _receive_json(ws)
        assert message["type"] == "error"
        assert message["code"] == "rate_limited"

        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_text()
        assert exc_info.value.code == PRESENCE_CLOSE_CODE


def test_websocket_rejects_other_users_sheet(
    client, second_user_headers, created_sheet
):
    ticket = client.post(
        f"/api/sheets/{created_sheet['id']}/ws-ticket",
        headers=second_user_headers,
    )
    assert ticket.status_code == 404
