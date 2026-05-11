from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import or_

from app.core.config import settings
from app.core.database import get_db
from app.core.request_context import client_ip_from_request
from app.core.rate_limit import (
    check_cell_edit_rate_limit,
    check_export_rate_limit,
    check_formula_preview_rate_limit,
    check_mutation_rate_limit,
    check_query_rate_limit,
)
from app.core.security import hash_token
from app.core.time import utc_now
from app.api.deps import get_current_user
from app.models.user import User
from app.models.dataset import (
    Chart as ChartModel,
    Comment as CommentModel,
    Dataset as DatasetModel,
    Sheet as SheetModel,
    SheetShare as SheetShareModel,
    WebSocketTicket as WebSocketTicketModel,
)
from app.schemas.dataset import (
    AggregateRequest,
    AggregateResult,
    CellUpdateRequest,
    CellUpdateResult,
    Comment,
    CommentCreate,
    DatasetData,
    DatasetQuery,
    FormulaPreviewRequest,
    FormulaPreviewResult,
    Sheet,
    SheetCreate,
    SheetExportRequest,
    SheetShare,
    SheetShareCreate,
    SheetUpdate,
    WebSocketTicketResponse,
)
from app.services.audit import record_audit_event
from app.services.dataset_store import (
    CellConflictError,
    QuerySpec,
    aggregate_dataset as aggregate_stored_dataset,
    count_records_for_export,
    full_records_for_export,
    query_dataset,
    update_cell as update_stored_cell,
)
from app.services.exporter import (
    content_disposition,
    records_to_csv_chunks,
    records_to_pdf,
    records_to_xlsx,
    safe_export_filename,
)
from app.services.permissions import require_sheet_role, sheet_role
from app.services.data_processor import DataProcessor
from app.services.dataset_store import dataframe_from_records, dataset_records
from app.services.websocket_manager import manager as websocket_manager

router = APIRouter()


def _sheet_to_schema(db: Session, sheet: SheetModel, current_user: User) -> dict:
    role = sheet_role(db, sheet, current_user)
    return {
        "id": sheet.id,
        "name": sheet.name,
        "description": sheet.description,
        "dataset_id": sheet.dataset_id,
        "owner_id": sheet.owner_id,
        "access_role": role or "viewer",
        "config": sheet.config,
        "created_at": sheet.created_at,
        "updated_at": sheet.updated_at,
    }


@router.post(
    "",
    response_model=Sheet,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(check_mutation_rate_limit)],
)
def create_sheet(
    sheet_in: SheetCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new sheet."""
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
    db.flush()
    record_audit_event(
        db,
        "sheet.created",
        "sheet",
        sheet.id,
        current_user,
        {"dataset_id": sheet.dataset_id, "name": sheet.name},
        request,
    )
    db.commit()
    db.refresh(sheet)

    return _sheet_to_schema(db, sheet, current_user)


@router.get("", response_model=List[Sheet])
def list_sheets(
    dataset_id: int = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all sheets for current user."""
    query = db.query(SheetModel).outerjoin(
        SheetShareModel, SheetShareModel.sheet_id == SheetModel.id
    ).filter(
        (SheetModel.owner_id == current_user.id) | (SheetShareModel.user_id == current_user.id)
    )
    
    if dataset_id:
        query = query.filter(SheetModel.dataset_id == dataset_id)
    
    sheets = query.offset(skip).limit(limit).all()
    return [_sheet_to_schema(db, sheet, current_user) for sheet in sheets]


@router.get("/{sheet_id}", response_model=Sheet)
def get_sheet(
    sheet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific sheet."""
    sheet = db.query(SheetModel).filter(SheetModel.id == sheet_id).first()
    
    if not sheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sheet not found"
        )
    require_sheet_role(db, sheet, current_user, "viewer")

    return _sheet_to_schema(db, sheet, current_user)


@router.post("/{sheet_id}/ws-ticket", response_model=WebSocketTicketResponse)
def create_websocket_ticket(
    sheet_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a short-lived, one-time WebSocket ticket for sheet collaboration."""
    sheet = _get_accessible_sheet(sheet_id, db, current_user, "viewer")
    ticket = secrets.token_urlsafe(32)
    expires_at = utc_now() + timedelta(seconds=settings.WS_TICKET_TTL_SECONDS)
    db.add(
        WebSocketTicketModel(
            ticket_hash=hash_token(ticket),
            sheet_id=sheet.id,
            user_id=current_user.id,
            expires_at=expires_at,
            ip_address=client_ip_from_request(request),
        )
    )
    record_audit_event(
        db,
        "websocket.ticket_created",
        "sheet",
        sheet.id,
        current_user,
        {},
        request,
    )
    db.commit()
    return {"ticket": ticket, "expires_at": expires_at}


@router.get(
    "/{sheet_id}/data",
    response_model=DatasetData,
    dependencies=[Depends(check_query_rate_limit)],
)
def get_sheet_data(
    sheet_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Read sheet rows through sheet-level permissions."""
    sheet = _get_accessible_sheet(sheet_id, db, current_user, "viewer")
    try:
        return query_dataset(
            db,
            sheet.dataset,
            QuerySpec(filters=[], page=page, page_size=page_size),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading sheet data: {str(e)}",
        )


@router.post(
    "/{sheet_id}/query",
    response_model=DatasetData,
    dependencies=[Depends(check_query_rate_limit)],
)
def query_sheet_data(
    sheet_id: int,
    sheet_query: DatasetQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Query sheet rows through sheet-level permissions."""
    sheet = _get_accessible_sheet(sheet_id, db, current_user, "viewer")
    try:
        return query_dataset(
            db,
            sheet.dataset,
            QuerySpec(
                filters=[item.model_dump() for item in sheet_query.filters],
                logic=sheet_query.logic,
                sort=sheet_query.sort.model_dump() if sheet_query.sort else None,
                page=sheet_query.page,
                page_size=sheet_query.page_size,
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{sheet_id}/aggregate",
    response_model=AggregateResult,
    dependencies=[Depends(check_query_rate_limit)],
)
def aggregate_sheet_data(
    sheet_id: int,
    agg_request: AggregateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aggregate sheet rows through sheet-level permissions."""
    sheet = _get_accessible_sheet(sheet_id, db, current_user, "viewer")
    try:
        return aggregate_stored_dataset(
            db,
            sheet.dataset,
            agg_request.column,
            agg_request.operation,
            agg_request.group_by,
            [filter_item.model_dump() for filter_item in agg_request.filters],
            agg_request.logic,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error aggregating sheet data: {str(e)}",
        )


def _get_owned_sheet(sheet_id: int, db: Session, current_user: User) -> SheetModel:
    sheet = db.query(SheetModel).filter(SheetModel.id == sheet_id).first()

    if not sheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sheet not found"
        )
    require_sheet_role(db, sheet, current_user, "owner")

    return sheet


def _get_accessible_sheet(
    sheet_id: int,
    db: Session,
    current_user: User,
    minimum_role: str = "viewer",
) -> SheetModel:
    sheet = db.query(SheetModel).filter(SheetModel.id == sheet_id).first()
    if not sheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sheet not found",
        )
    require_sheet_role(db, sheet, current_user, minimum_role)
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


def _share_to_schema(sheet: SheetModel, share: SheetShareModel | None = None) -> dict:
    if share is None:
        user = sheet.owner
        return {
            "id": 0,
            "sheet_id": sheet.id,
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "role": "owner",
            "created_at": sheet.created_at,
            "updated_at": sheet.updated_at,
        }
    return {
        "id": share.id,
        "sheet_id": share.sheet_id,
        "user_id": share.user_id,
        "username": share.user.username,
        "email": share.user.email,
        "role": share.role,
        "created_at": share.created_at,
        "updated_at": share.updated_at,
    }


@router.get("/{sheet_id}/comments", response_model=List[Comment])
def list_comments(
    sheet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List persisted comments for a sheet."""
    _get_accessible_sheet(sheet_id, db, current_user, "viewer")

    comments = db.query(CommentModel).filter(
        CommentModel.sheet_id == sheet_id
    ).order_by(CommentModel.created_at.asc(), CommentModel.id.asc()).all()

    return [_comment_to_schema(comment) for comment in comments]


@router.get("/{sheet_id}/shares", response_model=List[SheetShare])
def list_shares(
    sheet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List owner and explicit collaborators for a sheet."""
    sheet = _get_owned_sheet(sheet_id, db, current_user)
    shares = (
        db.query(SheetShareModel)
        .filter(SheetShareModel.sheet_id == sheet_id)
        .order_by(SheetShareModel.created_at.asc(), SheetShareModel.id.asc())
        .all()
    )
    return [_share_to_schema(sheet)] + [_share_to_schema(sheet, share) for share in shares]


@router.post(
    "/{sheet_id}/shares",
    response_model=SheetShare,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(check_mutation_rate_limit)],
)
def create_share(
    sheet_id: int,
    share_in: SheetShareCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Grant editor/viewer access to an existing user."""
    sheet = _get_owned_sheet(sheet_id, db, current_user)
    user = (
        db.query(User)
        .filter(
            or_(
                User.username == share_in.username_or_email,
                User.email == share_in.username_or_email,
            )
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == sheet.owner_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner already has access")

    share = (
        db.query(SheetShareModel)
        .filter(SheetShareModel.sheet_id == sheet_id, SheetShareModel.user_id == user.id)
        .first()
    )
    if share:
        share.role = share_in.role
    else:
        share = SheetShareModel(
            sheet_id=sheet_id,
            user_id=user.id,
            role=share_in.role,
            created_by_id=current_user.id,
        )
        db.add(share)
    db.flush()
    record_audit_event(
        db,
        "share.upserted",
        "sheet",
        sheet_id,
        current_user,
        {"target_user_id": user.id, "role": share.role},
        request,
    )
    db.commit()
    db.refresh(share)
    return _share_to_schema(sheet, share)


@router.delete(
    "/{sheet_id}/shares/{share_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(check_mutation_rate_limit)],
)
def delete_share(
    sheet_id: int,
    share_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a collaborator from a sheet."""
    _get_owned_sheet(sheet_id, db, current_user)
    share = (
        db.query(SheetShareModel)
        .filter(SheetShareModel.sheet_id == sheet_id, SheetShareModel.id == share_id)
        .first()
    )
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share not found")
    target_user_id = share.user_id
    db.delete(share)
    record_audit_event(
        db,
        "share.deleted",
        "sheet",
        sheet_id,
        current_user,
        {"target_user_id": target_user_id},
        request,
    )
    db.commit()
    background_tasks.add_task(
        websocket_manager.disconnect_user_from_sheet,
        sheet_id,
        target_user_id,
    )
    return None


@router.post(
    "/{sheet_id}/comments",
    response_model=Comment,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(check_mutation_rate_limit)],
)
def create_comment(
    sheet_id: int,
    comment_in: CommentCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a persisted sheet comment."""
    sheet = _get_accessible_sheet(sheet_id, db, current_user, "editor")

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
    db.flush()
    record_audit_event(
        db,
        "comment.created",
        "comment",
        comment.id,
        current_user,
        {"sheet_id": sheet_id, "row_index": comment_in.row_index, "column": comment_in.column},
        request,
    )
    db.commit()
    db.refresh(comment)
    background_tasks.add_task(
        websocket_manager.broadcast_to_sheet,
        sheet_id,
        {
            "type": "comment",
            "id": comment.id,
            "user_id": current_user.id,
            "username": current_user.username,
            "text": comment.text,
            "row_index": comment.row_index,
            "column": comment.column,
            "timestamp": comment.created_at.isoformat() if comment.created_at else None,
        },
    )

    return _comment_to_schema(comment)


@router.patch(
    "/{sheet_id}/cell",
    response_model=CellUpdateResult,
    dependencies=[Depends(check_cell_edit_rate_limit)],
)
def update_sheet_cell(
    sheet_id: int,
    cell_update: CellUpdateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update one sheet cell with optimistic conflict detection."""
    sheet = _get_accessible_sheet(sheet_id, db, current_user, "editor")
    try:
        result = update_stored_cell(
            db,
            sheet.dataset,
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
            "sheet",
            sheet_id,
            current_user,
            {
                "dataset_id": sheet.dataset_id,
                "row_index": cell_update.row_index,
                "column": cell_update.column,
                "version": result.get("version"),
                "forced": cell_update.force,
            },
            request,
        )
        db.commit()
        background_tasks.add_task(
            websocket_manager.broadcast_to_sheet,
            sheet_id,
            {
                "type": "cell_update",
                "user_id": current_user.id,
                "username": current_user.username,
                "row": result["row_index"],
                "row_index": result["row_index"],
                "column": result["column"],
                "value": result["value"],
                "formula": result.get("formula"),
                "version": result["version"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        return result
    except CellConflictError as e:
        record_audit_event(
            db,
            "cell.conflict",
            "sheet",
            sheet_id,
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{sheet_id}/formula-preview",
    response_model=FormulaPreviewResult,
    dependencies=[Depends(check_formula_preview_rate_limit)],
)
def preview_formula(
    sheet_id: int,
    preview_in: FormulaPreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Validate and evaluate a formula without saving it."""
    sheet = _get_accessible_sheet(sheet_id, db, current_user, "viewer")
    try:
        records = dataset_records(db, sheet.dataset)
        df = dataframe_from_records(records)
        formula_df = df.drop(columns=["__source_index"], errors="ignore")
        value = DataProcessor.evaluate_formula(
            formula_df,
            preview_in.value,
            target_row_index=preview_in.row_index,
            target_column=preview_in.column,
        )
        formula = preview_in.value.strip() if preview_in.value.strip().startswith("=") else None
        return {"valid": True, "value": value, "formula": formula, "error": None}
    except ValueError as e:
        return {"valid": False, "value": None, "formula": preview_in.value, "error": str(e)}


@router.post("/{sheet_id}/export", dependencies=[Depends(check_export_rate_limit)])
def export_sheet(
    sheet_id: int,
    export_in: SheetExportRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export a full filtered/sorted sheet to CSV, XLSX, or a simple PDF report."""
    sheet = _get_accessible_sheet(sheet_id, db, current_user, "viewer")
    filters = [filter_item.model_dump() for filter_item in export_in.filters]
    export_row_count = count_records_for_export(db, sheet.dataset, filters, export_in.logic)
    if export_row_count > settings.MAX_EXPORT_ROWS:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Export exceeds maximum of {settings.MAX_EXPORT_ROWS} rows",
        )
    records = full_records_for_export(
        db,
        sheet.dataset,
        filters,
        export_in.logic,
        export_in.sort.model_dump() if export_in.sort else None,
    )
    metadata = {
        "sheet_id": sheet.id,
        "dataset_id": sheet.dataset_id,
        "schema": sheet.dataset.schema if sheet.dataset else None,
        "filters": [filter_item.model_dump() for filter_item in export_in.filters],
        "sort": export_in.sort.model_dump() if export_in.sort else None,
        "include_comments": export_in.include_comments,
        "include_charts": export_in.include_charts,
    }
    if export_in.include_comments:
        comments = (
            db.query(CommentModel)
            .filter(CommentModel.sheet_id == sheet_id)
            .order_by(CommentModel.created_at.asc(), CommentModel.id.asc())
            .all()
        )
        metadata["comments"] = [
            {
                "id": comment.id,
                "username": comment.owner.username,
                "text": comment.text,
                "row_index": comment.row_index,
                "column": comment.column,
                "created_at": comment.created_at.isoformat() if comment.created_at else None,
            }
            for comment in comments
        ]
    if export_in.include_charts:
        charts = (
            db.query(ChartModel)
            .filter(ChartModel.sheet_id == sheet_id)
            .order_by(ChartModel.created_at.asc(), ChartModel.id.asc())
            .all()
        )
        metadata["charts"] = [
            {
                "id": chart.id,
                "name": chart.name,
                "chart_type": chart.chart_type,
                "config": chart.config,
            }
            for chart in charts
        ]

    if export_in.format == "xlsx":
        body = records_to_xlsx(records)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = safe_export_filename(sheet.name, "xlsx")
    elif export_in.format == "pdf":
        body = records_to_pdf(sheet.name, records, metadata)
        media_type = "application/pdf"
        filename = safe_export_filename(sheet.name, "pdf")
    else:
        media_type = "text/csv; charset=utf-8"
        filename = safe_export_filename(sheet.name, "csv")

    record_audit_event(
        db,
        "sheet.exported",
        "sheet",
        sheet_id,
        current_user,
        {"format": export_in.format, "row_count": len(records)},
        request,
    )
    db.commit()
    headers = {"Content-Disposition": content_disposition(filename)}
    if export_in.format == "csv":
        return StreamingResponse(
            records_to_csv_chunks(records),
            media_type=media_type,
            headers=headers,
        )
    return Response(content=body, media_type=media_type, headers=headers)


@router.put(
    "/{sheet_id}",
    response_model=Sheet,
    dependencies=[Depends(check_mutation_rate_limit)],
)
def update_sheet(
    sheet_id: int,
    sheet_update: SheetUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a sheet."""
    sheet = _get_accessible_sheet(sheet_id, db, current_user, "editor")
    
    update_data = sheet_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sheet, field, value)
    record_audit_event(
        db,
        "sheet.updated",
        "sheet",
        sheet_id,
        current_user,
        {"fields": sorted(update_data.keys())},
        request,
    )
    
    db.commit()
    db.refresh(sheet)
    
    return _sheet_to_schema(db, sheet, current_user)


@router.delete(
    "/{sheet_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(check_mutation_rate_limit)],
)
def delete_sheet(
    sheet_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a sheet."""
    sheet = _get_owned_sheet(sheet_id, db, current_user)
    record_audit_event(
        db,
        "sheet.deleted",
        "sheet",
        sheet_id,
        current_user,
        {"name": sheet.name, "dataset_id": sheet.dataset_id},
        request,
    )
    
    db.delete(sheet)
    db.commit()
    
    return None
