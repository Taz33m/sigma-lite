from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime


class DatasetBase(BaseModel):
    """Base dataset schema."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class DatasetCreate(DatasetBase):
    """Schema for dataset creation."""
    pass


class DatasetUpdate(BaseModel):
    """Schema for dataset update."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None


class Dataset(DatasetBase):
    """Public dataset schema."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    file_name: str
    file_size: int
    row_count: int
    column_count: int
    schema_: Optional[Dict[str, Any]] = Field(None, alias="schema")
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class DatasetData(BaseModel):
    """Schema for dataset data with pagination."""
    data: List[Dict[str, Any]]
    total_rows: int
    page: int
    page_size: int
    total_pages: int


class CellUpdateRequest(BaseModel):
    """Schema for updating one dataset cell."""
    row_index: int = Field(..., ge=0)
    column: str
    value: Any


class CellUpdateResult(BaseModel):
    """Schema for a cell update result."""
    row_index: int
    column: str
    value: Any


class FilterRequest(BaseModel):
    """Schema for filter request."""
    column: str
    operator: Literal[
        "eq",
        "ne",
        "gt",
        "lt",
        "gte",
        "lte",
        "contains",
        "startswith",
        "endswith",
    ]
    value: Any
    

class FilterQuery(BaseModel):
    """Schema for multiple filters."""
    filters: List[FilterRequest]
    logic: Literal["and", "or"] = "and"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=100, ge=1, le=1000)


class AggregateRequest(BaseModel):
    """Schema for aggregation request."""
    column: str
    operation: str  # sum, avg, min, max, count, median
    group_by: Optional[List[str]] = None


class AggregateResult(BaseModel):
    """Schema for aggregation result."""
    result: Any
    group_results: Optional[List[Dict[str, Any]]] = None


# Sheet schemas
class SheetBase(BaseModel):
    """Base sheet schema."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    dataset_id: int


class SheetCreate(SheetBase):
    """Schema for sheet creation."""
    config: Optional[Dict[str, Any]] = None


class SheetUpdate(BaseModel):
    """Schema for sheet update."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class Sheet(SheetBase):
    """Public sheet schema."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    config: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class CommentCreate(BaseModel):
    """Schema for creating a sheet comment."""
    text: str = Field(..., min_length=1, max_length=2000)
    row_index: Optional[int] = Field(None, ge=0)
    column: Optional[str] = None


class Comment(BaseModel):
    """Public sheet comment schema."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    sheet_id: int
    owner_id: int
    username: str
    text: str
    row_index: Optional[int] = None
    column: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# Chart schemas
class ChartBase(BaseModel):
    """Base chart schema."""
    name: str = Field(..., min_length=1, max_length=200)
    chart_type: str  # line, bar, scatter, pie
    sheet_id: int


class ChartCreate(ChartBase):
    """Schema for chart creation."""
    config: Dict[str, Any]


class ChartUpdate(BaseModel):
    """Schema for chart update."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    chart_type: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class Chart(ChartBase):
    """Public chart schema."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    config: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None
