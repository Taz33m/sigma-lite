from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil
from uuid import uuid4
from pathlib import Path

import pandas as pd
from app.core.database import get_db
from app.core.config import settings
from app.core.rate_limit import (
    check_cell_edit_rate_limit,
    check_mutation_rate_limit,
    check_query_rate_limit,
    check_upload_rate_limit,
)
from app.api.deps import get_current_user
from app.models.user import User
from app.models.dataset import (
    Dataset as DatasetModel,
    Sheet as SheetModel,
    SheetShare as SheetShareModel,
)
from app.schemas.dataset import (
    Dataset, DatasetCreate, DatasetUpdate, DatasetData,
    FilterQuery, AggregateRequest, AggregateResult, CellUpdateRequest,
    DatasetQuery,
    CellUpdateResult
)
from app.services.data_processor import DataProcessor
from app.services.audit import record_audit_event
from app.services.dataset_store import (
    CellConflictError,
    QuerySpec,
    aggregate_dataset as aggregate_stored_dataset,
    ensure_db_storage,
    ingest_dataframe,
    query_dataset,
    update_cell as update_stored_cell,
)

router = APIRouter()


def _get_accessible_dataset(
    db: Session,
    dataset_id: int,
    current_user: User,
    require_owner: bool = False,
    allow_shared_sheet_metadata: bool = False,
) -> DatasetModel:
    dataset = db.query(DatasetModel).filter(DatasetModel.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    if dataset.owner_id == current_user.id:
        return dataset
    if not require_owner and allow_shared_sheet_metadata:
        shared_sheet = (
            db.query(SheetModel.id)
            .outerjoin(SheetShareModel, SheetShareModel.sheet_id == SheetModel.id)
            .filter(
                SheetModel.dataset_id == dataset_id,
                SheetShareModel.user_id == current_user.id,
            )
            .first()
        )
        if shared_sheet:
            return dataset
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")


@router.post(
    "",
    response_model=Dataset,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(check_upload_rate_limit)],
)
async def upload_dataset(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a new dataset."""
    original_filename = Path(file.filename or "").name

    # Validate file type
    if Path(original_filename).suffix.lower() != ".csv":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported"
        )
    
    # Check file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE} bytes"
        )
    
    # Create user-specific upload directory
    user_upload_dir = Path(settings.UPLOAD_DIR) / str(current_user.id)
    user_upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Save file under a unique server-side name so repeated original filenames
    # do not overwrite each other for the same user.
    stored_filename = f"{uuid4().hex}.csv"
    file_path = user_upload_dir / stored_filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Process file
        processor = DataProcessor()
        df = processor.read_csv(str(file_path))
        schema = processor.infer_schema(df)
        
        # Create dataset record
        dataset = DatasetModel(
            name=name,
            description=description,
            file_name=original_filename,
            file_path=str(file_path),
            file_size=file_size,
            row_count=len(df),
            column_count=len(df.columns),
            schema=schema,
            owner_id=current_user.id
        )
        
        db.add(dataset)
        db.flush()
        ingest_dataframe(db, dataset, df, current_user.id)
        record_audit_event(
            db,
            "dataset.uploaded",
            "dataset",
            dataset.id,
            current_user,
            {"row_count": len(df), "column_count": len(df.columns), "file_name": original_filename},
            request,
        )
        db.commit()
        db.refresh(dataset)
        
        return dataset
    
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as e:
        # Clean up file if processing fails
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid CSV file: {str(e)}"
        )
    except Exception as e:
        # Clean up file if processing fails
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing file: {str(e)}"
        )


@router.get("", response_model=List[Dataset])
def list_datasets(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all datasets for current user."""
    datasets = db.query(DatasetModel).filter(
        DatasetModel.owner_id == current_user.id
    ).offset(skip).limit(limit).all()
    
    return datasets


@router.get("/{dataset_id}", response_model=Dataset)
def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific dataset."""
    return _get_accessible_dataset(
        db,
        dataset_id,
        current_user,
        allow_shared_sheet_metadata=True,
    )


@router.get(
    "/{dataset_id}/data",
    response_model=DatasetData,
    dependencies=[Depends(check_query_rate_limit)],
)
def get_dataset_data(
    dataset_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get dataset data with pagination."""
    dataset = _get_accessible_dataset(db, dataset_id, current_user)
    
    try:
        return query_dataset(
            db,
            dataset,
            QuerySpec(filters=[], page=page, page_size=page_size),
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading dataset: {str(e)}"
        )


@router.post(
    "/{dataset_id}/filter",
    response_model=DatasetData,
    dependencies=[Depends(check_query_rate_limit)],
)
def filter_dataset(
    dataset_id: int,
    filter_query: FilterQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Filter dataset data."""
    dataset = _get_accessible_dataset(db, dataset_id, current_user)
    
    try:
        filters = [f.model_dump() for f in filter_query.filters]
        return query_dataset(
            db,
            dataset,
            QuerySpec(
                filters=filters,
                logic=filter_query.logic,
                page=filter_query.page,
                page_size=filter_query.page_size,
            ),
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error filtering dataset: {str(e)}"
        )


@router.post(
    "/{dataset_id}/aggregate",
    response_model=AggregateResult,
    dependencies=[Depends(check_query_rate_limit)],
)
def aggregate_dataset(
    dataset_id: int,
    agg_request: AggregateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Aggregate dataset data."""
    dataset = _get_accessible_dataset(db, dataset_id, current_user)
    
    try:
        result = aggregate_stored_dataset(
            db,
            dataset,
            agg_request.column,
            agg_request.operation,
            agg_request.group_by,
            [filter_item.model_dump() for filter_item in agg_request.filters],
            agg_request.logic,
        )
        
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error aggregating dataset: {str(e)}"
        )


@router.patch(
    "/{dataset_id}/cell",
    response_model=CellUpdateResult,
    dependencies=[Depends(check_cell_edit_rate_limit)],
)
def update_dataset_cell(
    dataset_id: int,
    cell_update: CellUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Compatibility endpoint for owner-scoped cell updates."""
    dataset = db.query(DatasetModel).filter(
        DatasetModel.id == dataset_id,
        DatasetModel.owner_id == current_user.id
    ).first()

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )

    try:
        result = update_stored_cell(
            db,
            dataset,
            cell_update.row_index,
            cell_update.column,
            cell_update.value,
            current_user.id,
            cell_update.expected_version,
            cell_update.force,
        )
        record_audit_event(
            db,
            "cell.updated",
            "dataset",
            dataset_id,
            current_user,
            {
                "row_index": cell_update.row_index,
                "column": cell_update.column,
                "version": result.get("version"),
                "forced": cell_update.force,
            },
            request,
        )
        db.commit()

        return result

    except CellConflictError as e:
        record_audit_event(
            db,
            "cell.conflict",
            "dataset",
            dataset_id,
            current_user,
            {"row_index": e.row_index, "column": e.column, "current_version": e.current_version},
            request,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(e),
                "row_index": e.row_index,
                "column": e.column,
                "current_value": e.current_value,
                "current_version": e.current_version,
                "attempted_value": e.attempted_value,
            },
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating dataset cell: {str(e)}"
        )


@router.put(
    "/{dataset_id}",
    response_model=Dataset,
    dependencies=[Depends(check_mutation_rate_limit)],
)
def update_dataset(
    dataset_id: int,
    dataset_update: DatasetUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update dataset metadata."""
    dataset = db.query(DatasetModel).filter(
        DatasetModel.id == dataset_id,
        DatasetModel.owner_id == current_user.id
    ).first()
    
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    update_data = dataset_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dataset, field, value)
    record_audit_event(
        db,
        "dataset.updated",
        "dataset",
        dataset_id,
        current_user,
        {"fields": sorted(update_data.keys())},
        request,
    )
    
    db.commit()
    db.refresh(dataset)
    
    return dataset


@router.delete(
    "/{dataset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(check_mutation_rate_limit)],
)
def delete_dataset(
    dataset_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a dataset."""
    dataset = db.query(DatasetModel).filter(
        DatasetModel.id == dataset_id,
        DatasetModel.owner_id == current_user.id
    ).first()
    
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    # Delete file
    file_path = Path(dataset.file_path)
    if file_path.exists():
        file_path.unlink()
    
    record_audit_event(
        db,
        "dataset.deleted",
        "dataset",
        dataset_id,
        current_user,
        {"name": dataset.name, "file_name": dataset.file_name, "row_count": dataset.row_count},
        request,
    )

    # Delete database record
    db.delete(dataset)
    db.commit()
    
    return None


@router.post(
    "/{dataset_id}/query",
    response_model=DatasetData,
    dependencies=[Depends(check_query_rate_limit)],
)
def query_dataset_data(
    dataset_id: int,
    dataset_query: DatasetQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Query dataset rows with server-side filters, sorting, and pagination."""
    dataset = _get_accessible_dataset(db, dataset_id, current_user)

    try:
        return query_dataset(
            db,
            dataset,
            QuerySpec(
                filters=[item.model_dump() for item in dataset_query.filters],
                logic=dataset_query.logic,
                sort=dataset_query.sort.model_dump() if dataset_query.sort else None,
                page=dataset_query.page,
                page_size=dataset_query.page_size,
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
