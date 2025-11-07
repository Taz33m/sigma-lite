from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil
from pathlib import Path

from app.core.database import get_db
from app.core.config import settings
from app.api.deps import get_current_user
from app.models.user import User
from app.models.dataset import Dataset as DatasetModel
from app.schemas.dataset import (
    Dataset, DatasetCreate, DatasetUpdate, DatasetData,
    FilterQuery, AggregateRequest, AggregateResult
)
from app.services.data_processor import DataProcessor

router = APIRouter()


@router.post("", response_model=Dataset, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a new dataset."""
    # Validate file type
    if not file.filename.endswith('.csv'):
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
    
    # Save file
    file_path = user_upload_dir / file.filename
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
            file_name=file.filename,
            file_path=str(file_path),
            file_size=file_size,
            row_count=len(df),
            column_count=len(df.columns),
            schema=schema,
            owner_id=current_user.id
        )
        
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        
        return dataset
    
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
    skip: int = 0,
    limit: int = 100,
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
    dataset = db.query(DatasetModel).filter(
        DatasetModel.id == dataset_id,
        DatasetModel.owner_id == current_user.id
    ).first()
    
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    return dataset


@router.get("/{dataset_id}/data", response_model=DatasetData)
def get_dataset_data(
    dataset_id: int,
    page: int = 1,
    page_size: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get dataset data with pagination."""
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
        processor = DataProcessor()
        df = processor.read_csv(dataset.file_path)
        result = processor.get_data_page(df, page, page_size)
        
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading dataset: {str(e)}"
        )


@router.post("/{dataset_id}/filter", response_model=DatasetData)
def filter_dataset(
    dataset_id: int,
    filter_query: FilterQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Filter dataset data."""
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
        processor = DataProcessor()
        df = processor.read_csv(dataset.file_path)
        
        # Apply filters
        filters = [f.dict() for f in filter_query.filters]
        filtered_df = processor.apply_filters(df, filters, filter_query.logic)
        
        # Get paginated result
        result = processor.get_data_page(
            filtered_df,
            filter_query.page,
            filter_query.page_size
        )
        
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error filtering dataset: {str(e)}"
        )


@router.post("/{dataset_id}/aggregate", response_model=AggregateResult)
def aggregate_dataset(
    dataset_id: int,
    agg_request: AggregateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Aggregate dataset data."""
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
        processor = DataProcessor()
        df = processor.read_csv(dataset.file_path)
        
        result = processor.aggregate(
            df,
            agg_request.column,
            agg_request.operation,
            agg_request.group_by
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


@router.put("/{dataset_id}", response_model=Dataset)
def update_dataset(
    dataset_id: int,
    dataset_update: DatasetUpdate,
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
    
    update_data = dataset_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dataset, field, value)
    
    db.commit()
    db.refresh(dataset)
    
    return dataset


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(
    dataset_id: int,
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
    
    # Delete database record
    db.delete(dataset)
    db.commit()
    
    return None
