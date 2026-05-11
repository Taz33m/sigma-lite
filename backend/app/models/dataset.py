from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Dataset(Base):
    """Dataset model for storing uploaded data."""
    
    __tablename__ = "datasets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(BigInteger, nullable=False)
    row_count = Column(Integer, nullable=False, default=0)
    column_count = Column(Integer, nullable=False, default=0)
    schema = Column(JSON, nullable=True)  # Store column names and types
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="datasets")
    sheets = relationship("Sheet", back_populates="dataset", cascade="all, delete-orphan")
    columns = relationship("DatasetColumn", back_populates="dataset", cascade="all, delete-orphan")
    rows = relationship("DatasetRow", back_populates="dataset", cascade="all, delete-orphan")
    cells = relationship("DatasetCell", back_populates="dataset", cascade="all, delete-orphan")


class DatasetColumn(Base):
    """Column metadata for DB-backed dataset rows."""

    __tablename__ = "dataset_columns"
    __table_args__ = (
        UniqueConstraint("dataset_id", "name", name="uq_dataset_column_name"),
        Index("ix_dataset_columns_dataset_id", "dataset_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    name = Column(String, nullable=False)
    position = Column(Integer, nullable=False)
    data_type = Column(String, nullable=False)
    semantic_type = Column(String, nullable=False)
    stats = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    dataset = relationship("Dataset", back_populates="columns")
    cells = relationship("DatasetCell", back_populates="column_ref")


class DatasetRow(Base):
    """Source row identity for DB-backed dataset values."""

    __tablename__ = "dataset_rows"
    __table_args__ = (
        UniqueConstraint("dataset_id", "row_index", name="uq_dataset_row_index"),
        Index("ix_dataset_rows_dataset_id", "dataset_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    row_index = Column(Integer, nullable=False)
    values_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    dataset = relationship("Dataset", back_populates="rows")
    cells = relationship("DatasetCell", back_populates="row_ref", cascade="all, delete-orphan")


class DatasetCell(Base):
    """One persisted cell value with optimistic conflict metadata."""

    __tablename__ = "dataset_cells"
    __table_args__ = (
        UniqueConstraint("dataset_id", "row_index", "column_name", name="uq_dataset_cell"),
        Index("ix_dataset_cells_dataset_row", "dataset_id", "row_index"),
        Index("ix_dataset_cells_dataset_column", "dataset_id", "column_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    row_id = Column(Integer, ForeignKey("dataset_rows.id"), nullable=False)
    column_id = Column(Integer, ForeignKey("dataset_columns.id"), nullable=False)
    row_index = Column(Integer, nullable=False)
    column_name = Column(String, nullable=False)
    value = Column(JSON, nullable=True)
    formula = Column(String, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    dataset = relationship("Dataset", back_populates="cells")
    row_ref = relationship("DatasetRow", back_populates="cells")
    column_ref = relationship("DatasetColumn", back_populates="cells")
    updated_by = relationship("User")


class Sheet(Base):
    """Sheet model for saved workspaces."""
    
    __tablename__ = "sheets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    config = Column(JSON, nullable=True)  # Store filters, sorts, formulas
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    dataset = relationship("Dataset", back_populates="sheets")
    owner = relationship("User", back_populates="sheets")
    charts = relationship("Chart", back_populates="sheet", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="sheet", cascade="all, delete-orphan")
    shares = relationship("SheetShare", back_populates="sheet", cascade="all, delete-orphan")


class Chart(Base):
    """Chart model for visualizations."""
    
    __tablename__ = "charts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    chart_type = Column(String, nullable=False)  # line, bar, scatter, pie
    sheet_id = Column(Integer, ForeignKey("sheets.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    config = Column(JSON, nullable=False)  # Store chart configuration
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    sheet = relationship("Sheet", back_populates="charts")
    owner = relationship("User", back_populates="charts")


class Comment(Base):
    """Comment model for sheet collaboration."""

    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    sheet_id = Column(Integer, ForeignKey("sheets.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(String, nullable=False)
    row_index = Column(Integer, nullable=True)
    column = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    sheet = relationship("Sheet", back_populates="comments")
    owner = relationship("User", back_populates="comments")


class SheetShare(Base):
    """Role-based sheet access for collaborators."""

    __tablename__ = "sheet_shares"
    __table_args__ = (
        UniqueConstraint("sheet_id", "user_id", name="uq_sheet_share_user"),
        Index("ix_sheet_shares_sheet_id", "sheet_id"),
        Index("ix_sheet_shares_user_id", "user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    sheet_id = Column(Integer, ForeignKey("sheets.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    sheet = relationship("Sheet", back_populates="shares")
    user = relationship("User", foreign_keys=[user_id], back_populates="sheet_shares")
    created_by = relationship("User", foreign_keys=[created_by_id])


class AuditEvent(Base):
    """Append-only audit event for public-beta operations."""

    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_actor_created", "actor_id", "created_at"),
        Index("ix_audit_events_entity", "entity_type", "entity_id"),
        Index("ix_audit_events_action_created", "action", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)
    request_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    actor = relationship("User", back_populates="audit_events")


class WebSocketTicket(Base):
    """One-time ticket for sheet collaboration WebSocket connections."""

    __tablename__ = "websocket_tickets"
    __table_args__ = (
        Index("ix_websocket_tickets_hash", "ticket_hash", unique=True),
        Index("ix_websocket_tickets_sheet_user", "sheet_id", "user_id"),
        Index("ix_websocket_tickets_expires", "expires_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    ticket_hash = Column(String, nullable=False, unique=True)
    sheet_id = Column(Integer, ForeignKey("sheets.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sheet = relationship("Sheet")
    user = relationship("User")
