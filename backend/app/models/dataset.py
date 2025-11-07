from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, BigInteger
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
