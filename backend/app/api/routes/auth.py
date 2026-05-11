from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.request_context import client_ip_from_request
from app.core.rate_limit import check_auth_identity_rate_limit, check_auth_rate_limit
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    hash_token,
    verify_password,
)
from app.core.time import ensure_aware_utc, utc_now
from app.api.deps import get_current_user
from app.models.user import RefreshToken, User
from app.schemas.user import LogoutRequest, RefreshTokenRequest, UserCreate, User as UserSchema, Token
from app.services.audit import record_audit_event

router = APIRouter()


def _refresh_expires_at(payload: dict | None = None) -> datetime:
    if payload and payload.get("exp") is not None:
        try:
            return datetime.fromtimestamp(int(payload["exp"]), timezone.utc)
        except (TypeError, ValueError, OSError):
            pass

    return utc_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


def _store_refresh_token(
    db: Session,
    user: User,
    request: Request,
    *,
    family_id: str | None = None,
) -> str:
    jti = uuid4().hex
    resolved_family_id = family_id or uuid4().hex
    token = create_refresh_token(
        data={"sub": str(user.id)},
        jti=jti,
        family_id=resolved_family_id,
    )
    payload = decode_token(token) or {}
    db.add(
        RefreshToken(
            jti=jti,
            family_id=resolved_family_id,
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=_refresh_expires_at(payload),
            ip_address=client_ip_from_request(request),
            user_agent=request.headers.get("user-agent"),
        )
    )
    return token


def _invalid_refresh_token() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
    )


def _revoke_refresh_family(db: Session, family_id: str, when: datetime) -> None:
    (
        db.query(RefreshToken)
        .filter(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .update({"revoked_at": when}, synchronize_session=False)
    )


def _refresh_record_from_token(db: Session, token: str) -> tuple[RefreshToken, dict]:
    payload = decode_token(token)
    if payload is None or payload.get("type") != "refresh":
        raise _invalid_refresh_token()
    jti = payload.get("jti")
    family_id = payload.get("family_id")
    user_id = payload.get("sub")
    if not jti or not family_id or not user_id:
        raise _invalid_refresh_token()
    try:
        int(user_id)
    except (TypeError, ValueError):
        raise _invalid_refresh_token()

    record = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
    if not record or record.token_hash != hash_token(token):
        raise _invalid_refresh_token()
    return record, payload


@router.post(
    "/register",
    response_model=UserSchema,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(check_auth_rate_limit)],
)
def register(
    user_in: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Register a new user."""
    check_auth_identity_rate_limit(request, db, user_in.username)
    check_auth_identity_rate_limit(request, db, user_in.email)
    # Check if user already exists
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    user = db.query(User).filter(User.username == user_in.username).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create new user
    user = User(
        email=user_in.email,
        username=user_in.username,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password)
    )
    
    db.add(user)
    db.flush()
    record_audit_event(
        db,
        "auth.registered",
        "user",
        user.id,
        user,
        {"username": user.username},
        request,
    )
    db.commit()
    db.refresh(user)
    
    return user


@router.post(
    "/login",
    response_model=Token,
    dependencies=[Depends(check_auth_rate_limit)],
)
def login(
    request: Request,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """Login and get access token."""
    check_auth_identity_rate_limit(request, db, form_data.username)
    # Find user by username
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        record_audit_event(
            db,
            "auth.login_failed",
            "user",
            user.id if user else None,
            user if user else None,
            {"username": form_data.username},
            request,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Create tokens (JWT spec requires `sub` to be a string)
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = _store_refresh_token(db, user, request)
    record_audit_event(
        db,
        "auth.login_succeeded",
        "user",
        user.id,
        user,
        {"username": user.username},
        request,
    )
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserSchema)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the current authenticated user."""
    return current_user


@router.post(
    "/refresh",
    response_model=Token,
    dependencies=[Depends(check_auth_rate_limit)],
)
def refresh_token(
    token_in: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Refresh access token using refresh token."""
    record, payload = _refresh_record_from_token(db, token_in.token)
    now = utc_now()
    if (
        record.revoked_at is not None
        or record.rotated_at is not None
        or ensure_aware_utc(record.expires_at) <= now
    ):
        _revoke_refresh_family(db, record.family_id, now)
        record_audit_event(
            db,
            "auth.refresh_reuse_blocked",
            "user",
            record.user_id,
            actor_id=record.user_id,
            metadata={"family_id": record.family_id},
            request=request,
        )
        db.commit()
        raise _invalid_refresh_token()

    user = db.query(User).filter(User.id == int(payload["sub"])).first()

    if not user or not user.is_active:
        raise _invalid_refresh_token()

    # Create new tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = _store_refresh_token(db, user, request, family_id=record.family_id)
    new_payload = decode_token(new_refresh_token) or {}
    record.rotated_at = now
    record.replaced_by_jti = new_payload.get("jti")
    record_audit_event(
        db,
        "auth.refresh_succeeded",
        "user",
        user.id,
        user,
        {"username": user.username, "family_id": record.family_id},
        request,
    )
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    logout_in: LogoutRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke refresh-token state for the current user."""
    now = utc_now()
    if logout_in.all_sessions:
        (
            db.query(RefreshToken)
            .filter(RefreshToken.user_id == current_user.id, RefreshToken.revoked_at.is_(None))
            .update({"revoked_at": now}, synchronize_session=False)
        )
        record_audit_event(
            db,
            "auth.logout_all",
            "user",
            current_user.id,
            current_user,
            {},
            request,
        )
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    if logout_in.refresh_token:
        try:
            record, _ = _refresh_record_from_token(db, logout_in.refresh_token)
        except HTTPException:
            record = None
        if record and record.user_id == current_user.id and record.revoked_at is None:
            record.revoked_at = now

    record_audit_event(
        db,
        "auth.logout",
        "user",
        current_user.id,
        current_user,
        {},
        request,
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
