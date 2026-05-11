"""Sheet access helpers."""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.dataset import Sheet, SheetShare
from app.models.user import User


ROLE_ORDER = {"viewer": 1, "editor": 2, "owner": 3}


def sheet_role(db: Session, sheet: Sheet, user: User) -> str | None:
    if sheet.owner_id == user.id:
        return "owner"
    share = (
        db.query(SheetShare)
        .filter(SheetShare.sheet_id == sheet.id, SheetShare.user_id == user.id)
        .first()
    )
    return share.role if share else None


def require_sheet_role(db: Session, sheet: Sheet, user: User, minimum: str) -> str:
    role = sheet_role(db, sheet, user)
    if not role or ROLE_ORDER[role] < ROLE_ORDER[minimum]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if minimum == "viewer" else status.HTTP_403_FORBIDDEN,
            detail="Sheet not found" if minimum == "viewer" else "Not enough sheet permissions",
        )
    return role
