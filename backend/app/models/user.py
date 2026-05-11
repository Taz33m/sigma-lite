from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    """User model."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    datasets = relationship("Dataset", back_populates="owner", cascade="all, delete-orphan")
    sheets = relationship("Sheet", back_populates="owner", cascade="all, delete-orphan")
    charts = relationship("Chart", back_populates="owner", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="owner", cascade="all, delete-orphan")
    sheet_shares = relationship(
        "SheetShare",
        foreign_keys="SheetShare.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    audit_events = relationship("AuditEvent", back_populates="actor")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    """Persisted refresh-token rotation state."""

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_tokens_jti", "jti", unique=True),
        Index("ix_refresh_tokens_user_active", "user_id", "revoked_at", "expires_at"),
        Index("ix_refresh_tokens_family", "family_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String, nullable=False, unique=True)
    family_id = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    rotated_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    replaced_by_jti = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="refresh_tokens")
