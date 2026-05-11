"""Audit event helpers."""
from typing import Any, Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.request_context import client_ip_from_request
from app.models.dataset import AuditEvent
from app.models.user import User


def _request_ip_address(request: Request | None) -> str | None:
    return client_ip_from_request(request)


def record_audit_event(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: Optional[int] = None,
    actor: Optional[User] = None,
    metadata: Optional[dict[str, Any]] = None,
    request: Optional[Request] = None,
    actor_id: Optional[int] = None,
) -> None:
    request_id = getattr(request.state, "request_id", None) if request else None
    ip_address = _request_ip_address(request)
    resolved_actor_id = actor.id if actor else actor_id
    db.add(
        AuditEvent(
            actor_id=resolved_actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata or {},
            ip_address=ip_address,
            request_id=request_id,
        )
    )
