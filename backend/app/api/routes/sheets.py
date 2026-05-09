from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.dataset import (
    Comment as CommentModel,
    Dataset as DatasetModel,
    Sheet as SheetModel,
)
from app.schemas.dataset import Comment, CommentCreate, Sheet, SheetCreate, SheetUpdate

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


def _get_owned_sheet(sheet_id: int, db: Session, current_user: User) -> SheetModel:
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


def _comment_to_schema(comment: CommentModel) -> dict:
    return {
        "id": comment.id,
        "sheet_id": comment.sheet_id,
        "owner_id": comment.owner_id,
        "username": comment.owner.username,
        "text": comment.text,
        "row_index": comment.row_index,
        "column": comment.column,
        "created_at": comment.created_at,
        "updated_at": comment.updated_at,
    }


@router.get("/{sheet_id}/comments", response_model=List[Comment])
def list_comments(
    sheet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List persisted comments for a sheet."""
    _get_owned_sheet(sheet_id, db, current_user)

    comments = db.query(CommentModel).filter(
        CommentModel.sheet_id == sheet_id
    ).order_by(CommentModel.created_at.asc(), CommentModel.id.asc()).all()

    return [_comment_to_schema(comment) for comment in comments]


@router.post(
    "/{sheet_id}/comments",
    response_model=Comment,
    status_code=status.HTTP_201_CREATED
)
def create_comment(
    sheet_id: int,
    comment_in: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a persisted sheet comment."""
    sheet = _get_owned_sheet(sheet_id, db, current_user)

    if comment_in.row_index is not None:
        row_count = sheet.dataset.row_count if sheet.dataset else 0
        if comment_in.row_index >= row_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Comment row index is outside the dataset",
            )

    if comment_in.column is not None:
        columns = []
        if sheet.dataset and sheet.dataset.schema:
            columns = [
                column.get("name")
                for column in sheet.dataset.schema.get("columns", [])
            ]
        if comment_in.column not in columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Column '{comment_in.column}' not found",
            )

    comment = CommentModel(
        sheet_id=sheet_id,
        owner_id=current_user.id,
        text=comment_in.text,
        row_index=comment_in.row_index,
        column=comment_in.column,
    )

    db.add(comment)
    db.commit()
    db.refresh(comment)

    return _comment_to_schema(comment)


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
    
    update_data = sheet_update.model_dump(exclude_unset=True)
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
