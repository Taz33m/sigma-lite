from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.core.config import settings
from app.models.user import User
from app.schemas.user import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"/api/auth/login", auto_error=False)


def get_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme)
) -> User:
    """Get current authenticated user."""
    # If authentication is disabled, return a mock user
    if settings.DISABLE_AUTH:
        # Check if demo user exists, create if not
        demo_user = db.query(User).filter(User.username == "demo_user").first()
        if not demo_user:
            # Use a dummy hash since auth is disabled anyway
            demo_user = User(
                email="demo@sigmalite.com",
                username="demo_user",
                full_name="Demo User",
                hashed_password="$2b$12$dummy_hash_not_used_when_auth_disabled",
                is_active=True,
                is_superuser=False
            )
            db.add(demo_user)
            db.commit()
            db.refresh(demo_user)
        return demo_user
    
    # Normal authentication flow
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    
    token_data = TokenPayload(**payload)
    
    if token_data.sub is None:
        raise credentials_exception
    
    if token_data.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )
    
    user = db.query(User).filter(User.id == token_data.sub).first()
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user


def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges"
        )
    return current_user
