from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.dataset import Sheet as SheetModel, Dataset as DatasetModel
from app.schemas.dataset import Sheet, SheetCreate, SheetUpdate

router = APIRouter()


@router.post("", response_model=Sheet, status_code=status.HTTP_201_CREATED)
def create_sheet(
    sheet_in: SheetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new sheet."""
    # Verify dataset exists and belongs to user
    dataset = db.query(DatasetModel).filter(
        DatasetModel.id == sheet_in.dataset_id,
        DatasetModel.owner_id == current_user.id
    ).first()
    
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    sheet = SheetModel(
        name=sheet_in.name,
        description=sheet_in.description,
        dataset_id=sheet_in.dataset_id,
        owner_id=current_user.id,
        config=sheet_in.config or {}
    )
    
    db.add(sheet)
    db.commit()
    db.refresh(sheet)
    
    return sheet


@router.get("", response_model=List[Sheet])
def list_sheets(
    dataset_id: int = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all sheets for current user."""
    query = db.query(SheetModel).filter(SheetModel.owner_id == current_user.id)
    
    if dataset_id:
        query = query.filter(SheetModel.dataset_id == dataset_id)
    
    sheets = query.offset(skip).limit(limit).all()
    return sheets


@router.get("/{sheet_id}", response_model=Sheet)
def get_sheet(
    sheet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific sheet."""
    sheet = db.query(SheetModel).filter(
        SheetModel.id == sheet_id,
        SheetModel.owner_id == current_user.id
    ).first()
    
    if not sheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sheet not found"
        )
    
    return sheet


@router.put("/{sheet_id}", response_model=Sheet)
def update_sheet(
    sheet_id: int,
    sheet_update: SheetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a sheet."""
    sheet = db.query(SheetModel).filter(
        SheetModel.id == sheet_id,
        SheetModel.owner_id == current_user.id
    ).first()
    
    if not sheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sheet not found"
        )
    
    update_data = sheet_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sheet, field, value)
    
    db.commit()
    db.refresh(sheet)
    
    return sheet


@router.delete("/{sheet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sheet(
    sheet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a sheet."""
    sheet = db.query(SheetModel).filter(
        SheetModel.id == sheet_id,
        SheetModel.owner_id == current_user.id
    ).first()
    
    if not sheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sheet not found"
        )
    
    db.delete(sheet)
    db.commit()
    
    return None
