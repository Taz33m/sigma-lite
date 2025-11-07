from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.dataset import Chart as ChartModel, Sheet as SheetModel
from app.schemas.dataset import Chart, ChartCreate, ChartUpdate

router = APIRouter()


@router.post("", response_model=Chart, status_code=status.HTTP_201_CREATED)
def create_chart(
    chart_in: ChartCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new chart."""
    # Verify sheet exists and belongs to user
    sheet = db.query(SheetModel).filter(
        SheetModel.id == chart_in.sheet_id,
        SheetModel.owner_id == current_user.id
    ).first()
    
    if not sheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sheet not found"
        )
    
    # Validate chart type
    valid_types = ["line", "bar", "scatter", "pie"]
    if chart_in.chart_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid chart type. Must be one of: {', '.join(valid_types)}"
        )
    
    chart = ChartModel(
        name=chart_in.name,
        chart_type=chart_in.chart_type,
        sheet_id=chart_in.sheet_id,
        owner_id=current_user.id,
        config=chart_in.config
    )
    
    db.add(chart)
    db.commit()
    db.refresh(chart)
    
    return chart


@router.get("", response_model=List[Chart])
def list_charts(
    sheet_id: int = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all charts for current user."""
    query = db.query(ChartModel).filter(ChartModel.owner_id == current_user.id)
    
    if sheet_id:
        query = query.filter(ChartModel.sheet_id == sheet_id)
    
    charts = query.offset(skip).limit(limit).all()
    return charts


@router.get("/{chart_id}", response_model=Chart)
def get_chart(
    chart_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific chart."""
    chart = db.query(ChartModel).filter(
        ChartModel.id == chart_id,
        ChartModel.owner_id == current_user.id
    ).first()
    
    if not chart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chart not found"
        )
    
    return chart


@router.put("/{chart_id}", response_model=Chart)
def update_chart(
    chart_id: int,
    chart_update: ChartUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a chart."""
    chart = db.query(ChartModel).filter(
        ChartModel.id == chart_id,
        ChartModel.owner_id == current_user.id
    ).first()
    
    if not chart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chart not found"
        )
    
    update_data = chart_update.dict(exclude_unset=True)
    
    # Validate chart type if being updated
    if "chart_type" in update_data:
        valid_types = ["line", "bar", "scatter", "pie"]
        if update_data["chart_type"] not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid chart type. Must be one of: {', '.join(valid_types)}"
            )
    
    for field, value in update_data.items():
        setattr(chart, field, value)
    
    db.commit()
    db.refresh(chart)
    
    return chart


@router.delete("/{chart_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chart(
    chart_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a chart."""
    chart = db.query(ChartModel).filter(
        ChartModel.id == chart_id,
        ChartModel.owner_id == current_user.id
    ).first()
    
    if not chart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chart not found"
        )
    
    db.delete(chart)
    db.commit()
    
    return None
