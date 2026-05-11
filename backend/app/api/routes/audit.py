from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.dataset import (
    AuditEvent as AuditEventModel,
    Dataset as DatasetModel,
    Sheet as SheetModel,
)
from app.models.user import User
from app.schemas.dataset import AuditEvent

router = APIRouter()

SENSITIVE_METADATA_KEYS = {
    "email",
    "ip_address",
    "target_user_id",
    "target_email",
    "target_user_email",
    "token",
    "refresh_token",
    "access_token",
    "family_id",
    "jti",
}


def _redacted_metadata(metadata: dict | None) -> dict | None:
    if metadata is None:
        return None
    redacted = {}
    for key, value in metadata.items():
        if key.lower() in SENSITIVE_METADATA_KEYS:
            continue
        redacted[key] = value
    return redacted


def _audit_to_schema(event: AuditEventModel, *, include_private: bool) -> dict:
    return {
        "id": event.id,
        "actor_id": event.actor_id,
        "action": event.action,
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "metadata": event.metadata_json if include_private else _redacted_metadata(event.metadata_json),
        "ip_address": event.ip_address if include_private else None,
        "request_id": event.request_id,
        "created_at": event.created_at,
    }


@router.get("", response_model=List[AuditEvent])
def list_audit_events(
    actor_id: Optional[int] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List audit events visible to the current user."""
    query = db.query(AuditEventModel)
    if current_user.is_superuser:
        if actor_id is not None:
            query = query.filter(AuditEventModel.actor_id == actor_id)
    else:
        owned_sheet_ids = [
            sheet_id
            for (sheet_id,) in db.query(SheetModel.id)
            .filter(SheetModel.owner_id == current_user.id)
            .all()
        ]
        owned_dataset_ids = [
            dataset_id
            for (dataset_id,) in db.query(DatasetModel.id)
            .filter(DatasetModel.owner_id == current_user.id)
            .all()
        ]
        visibility_clauses = [AuditEventModel.actor_id == current_user.id]
        if owned_sheet_ids:
            visibility_clauses.append(
                and_(
                    AuditEventModel.entity_type == "sheet",
                    AuditEventModel.entity_id.in_(owned_sheet_ids),
                )
            )
            visibility_clauses.append(
                AuditEventModel.metadata_json["sheet_id"].as_integer().in_(owned_sheet_ids)
            )
        if owned_dataset_ids:
            visibility_clauses.append(
                and_(
                    AuditEventModel.entity_type == "dataset",
                    AuditEventModel.entity_id.in_(owned_dataset_ids),
                )
            )
        query = query.filter(or_(*visibility_clauses))
        if actor_id is not None:
            query = query.filter(AuditEventModel.actor_id == actor_id)
    if entity_type:
        query = query.filter(AuditEventModel.entity_type == entity_type)
    if entity_id is not None:
        query = query.filter(AuditEventModel.entity_id == entity_id)
    events = query.order_by(AuditEventModel.created_at.desc(), AuditEventModel.id.desc()).limit(limit).all()
    return [_audit_to_schema(event, include_private=current_user.is_superuser) for event in events]
