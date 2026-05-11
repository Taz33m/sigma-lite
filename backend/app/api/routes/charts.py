from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.rate_limit import check_mutation_rate_limit
from app.api.deps import get_current_user
from app.models.user import User
from app.models.dataset import Chart as ChartModel, Sheet as SheetModel, SheetShare
from app.schemas.dataset import Chart, ChartCreate, ChartUpdate
from app.services.audit import record_audit_event
from app.services.permissions import require_sheet_role

router = APIRouter()


@router.post(
    "",
    response_model=Chart,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(check_mutation_rate_limit)],
)
def create_chart(
    chart_in: ChartCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new chart."""
    sheet = db.query(SheetModel).filter(SheetModel.id == chart_in.sheet_id).first()
    
    if not sheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sheet not found"
        )
    require_sheet_role(db, sheet, current_user, "editor")
    
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
    db.flush()
    record_audit_event(
        db,
        "chart.created",
        "chart",
        chart.id,
        current_user,
        {"sheet_id": chart.sheet_id, "chart_type": chart.chart_type},
        request,
    )
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
    if sheet_id:
        sheet = db.query(SheetModel).filter(SheetModel.id == sheet_id).first()
        if not sheet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sheet not found")
        require_sheet_role(db, sheet, current_user, "viewer")
        query = db.query(ChartModel).filter(ChartModel.sheet_id == sheet_id)
    else:
        query = (
            db.query(ChartModel)
            .join(SheetModel, SheetModel.id == ChartModel.sheet_id)
            .outerjoin(SheetShare, SheetShare.sheet_id == SheetModel.id)
            .filter(
                or_(
                    SheetModel.owner_id == current_user.id,
                    SheetShare.user_id == current_user.id,
                )
            )
        )

    charts = query.offset(skip).limit(limit).all()
    return charts


@router.get("/{chart_id}", response_model=Chart)
def get_chart(
    chart_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific chart."""
    chart = db.query(ChartModel).filter(ChartModel.id == chart_id).first()

    if not chart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chart not found"
        )
    require_sheet_role(db, chart.sheet, current_user, "viewer")
    
    return chart


@router.put(
    "/{chart_id}",
    response_model=Chart,
    dependencies=[Depends(check_mutation_rate_limit)],
)
def update_chart(
    chart_id: int,
    chart_update: ChartUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a chart."""
    chart = db.query(ChartModel).filter(ChartModel.id == chart_id).first()
    
    if not chart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chart not found"
        )
    require_sheet_role(db, chart.sheet, current_user, "editor")

    update_data = chart_update.model_dump(exclude_unset=True)
    
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

    record_audit_event(
        db,
        "chart.updated",
        "chart",
        chart.id,
        current_user,
        {"sheet_id": chart.sheet_id, "fields": sorted(update_data.keys())},
        request,
    )
    db.commit()
    db.refresh(chart)
    
    return chart


@router.delete(
    "/{chart_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(check_mutation_rate_limit)],
)
def delete_chart(
    chart_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a chart."""
    chart = db.query(ChartModel).filter(ChartModel.id == chart_id).first()
    
    if not chart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chart not found"
        )
    require_sheet_role(db, chart.sheet, current_user, "editor")

    record_audit_event(
        db,
        "chart.deleted",
        "chart",
        chart.id,
        current_user,
        {"sheet_id": chart.sheet_id, "chart_type": chart.chart_type},
        request,
    )
    db.delete(chart)
    db.commit()
    
    return None
