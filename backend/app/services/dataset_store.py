"""DB-backed dataset row/cell storage and query helpers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd
from sqlalchemy import Float, String, and_, cast, func, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.dataset import (
    Dataset,
    DatasetCell,
    DatasetColumn,
    DatasetRow,
)
from app.services.data_processor import DataProcessor


class CellConflictError(ValueError):
    """Raised when a cell update is based on a stale version."""

    def __init__(
        self,
        row_index: int,
        column: str,
        current_value: Any,
        current_version: int,
        attempted_value: Any,
    ) -> None:
        self.row_index = row_index
        self.column = column
        self.current_value = current_value
        self.current_version = current_version
        self.attempted_value = attempted_value
        super().__init__("Cell was updated by someone else")


@dataclass
class QuerySpec:
    filters: List[Dict[str, Any]]
    logic: str = "and"
    sort: Optional[Dict[str, str]] = None
    page: int = 1
    page_size: int = 100


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and np.isnan(value):
        return None
    if pd.isna(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def _schema_column_stats(column_info: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: value
        for key, value in column_info.items()
        if key not in {"name", "type", "semantic_type"}
    }


def ingest_dataframe(
    db: Session,
    dataset: Dataset,
    df: pd.DataFrame,
    user_id: Optional[int] = None,
) -> None:
    """Ingest a DataFrame into normalized row/cell tables."""
    db.query(DatasetCell).filter(DatasetCell.dataset_id == dataset.id).delete()
    db.query(DatasetRow).filter(DatasetRow.dataset_id == dataset.id).delete()
    db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset.id).delete()
    db.flush()

    processor = DataProcessor()
    schema = processor.infer_schema(df)
    columns: List[DatasetColumn] = []
    for position, column_info in enumerate(schema["columns"]):
        column = DatasetColumn(
            dataset_id=dataset.id,
            name=column_info["name"],
            position=position,
            data_type=column_info["type"],
            semantic_type=column_info["semantic_type"],
            stats=_schema_column_stats(column_info),
        )
        columns.append(column)
    db.add_all(columns)
    db.flush()

    rows: List[DatasetRow] = [
        DatasetRow(
            dataset_id=dataset.id,
            row_index=int(index),
            values_json={
                str(column_name): _json_safe(row[column_name])
                for column_name in df.columns
            },
        )
        for index, row in df.iterrows()
    ]
    db.add_all(rows)
    db.flush()

    cells: List[DatasetCell] = []
    column_by_name = {column.name: column for column in columns}
    row_by_index = {row.row_index: row for row in rows}
    for row_index, row in df.iterrows():
        row_ref = row_by_index[int(row_index)]
        for column_name in df.columns:
            column_ref = column_by_name[str(column_name)]
            cells.append(
                DatasetCell(
                    dataset_id=dataset.id,
                    row_id=row_ref.id,
                    column_id=column_ref.id,
                    row_index=int(row_index),
                    column_name=str(column_name),
                    value=_json_safe(row[column_name]),
                    version=1,
                    updated_by_id=user_id,
                )
            )
        if len(cells) >= 5000:
            db.add_all(cells)
            db.flush()
            cells = []
    if cells:
        db.add_all(cells)

    dataset.row_count = len(df)
    dataset.column_count = len(df.columns)
    dataset.schema = schema


def has_db_storage(db: Session, dataset: Dataset) -> bool:
    return (
        db.query(DatasetColumn)
        .filter(DatasetColumn.dataset_id == dataset.id)
        .limit(1)
        .first()
        is not None
    )


def ensure_db_storage(db: Session, dataset: Dataset) -> None:
    """Backfill legacy CSV-only datasets into DB-backed storage on first use."""
    if has_db_storage(db, dataset):
        return
    if not dataset.file_path or not Path(dataset.file_path).exists():
        raise ValueError("Dataset backing file is missing")
    df = DataProcessor.read_csv(dataset.file_path)
    ingest_dataframe(db, dataset, df, dataset.owner_id)
    db.commit()
    db.refresh(dataset)


def dataset_records(
    db: Session,
    dataset: Dataset,
    include_cell_metadata: bool = True,
    row_indexes: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    ensure_db_storage(db, dataset)
    columns = (
        db.query(DatasetColumn)
        .filter(DatasetColumn.dataset_id == dataset.id)
        .order_by(DatasetColumn.position.asc())
        .all()
    )
    row_query = db.query(DatasetRow).filter(DatasetRow.dataset_id == dataset.id)
    if row_indexes is not None:
        row_query = row_query.filter(DatasetRow.row_index.in_(row_indexes))
    rows = row_query.order_by(DatasetRow.row_index.asc()).all()
    records: Dict[int, Dict[str, Any]] = {
        row.row_index: {column.name: None for column in columns}
        | (row.values_json or {})
        | {"__source_index": row.row_index}
        for row in rows
    }
    if not include_cell_metadata:
        return [records[row.row_index] for row in rows]

    cells = (
        db.query(DatasetCell)
        .filter(DatasetCell.dataset_id == dataset.id)
    )
    if row_indexes is not None:
        cells = cells.filter(DatasetCell.row_index.in_(row_indexes))
    for cell in cells.order_by(DatasetCell.row_index.asc(), DatasetCell.column_name.asc()).all():
        record = records.setdefault(
            cell.row_index,
            {"__source_index": cell.row_index},
        )
        record.setdefault("__cell_versions", {})[cell.column_name] = cell.version
        if cell.formula is not None:
            record.setdefault("__cell_formulas", {})[cell.column_name] = cell.formula
    return [records[row.row_index] for row in rows]


def _records_for_dataframe(db: Session, dataset: Dataset) -> List[Dict[str, Any]]:
    return dataset_records(db, dataset, include_cell_metadata=False)


def _page_records_with_metadata(
    db: Session,
    dataset: Dataset,
    source_indexes: List[int],
) -> List[Dict[str, Any]]:
    records = dataset_records(
        db,
        dataset,
        include_cell_metadata=True,
        row_indexes=source_indexes,
    )
    records_by_index = {record["__source_index"]: record for record in records}
    return [records_by_index[index] for index in source_indexes if index in records_by_index]


def dataframe_from_records(records: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    visible_records = [
        {key: value for key, value in record.items() if not key.startswith("__")}
        | {"__source_index": record["__source_index"]}
        for record in records
    ]
    return pd.DataFrame(visible_records)


def _source_index_for_position(df: pd.DataFrame, position: int) -> int:
    if "__source_index" in df.columns:
        return int(df.iloc[position]["__source_index"])
    return position


def _formula_dependency_cells(df: pd.DataFrame, formula: str) -> set[tuple[int, str]]:
    expression = formula.strip()
    if not expression.startswith("="):
        return set()
    expression = expression[1:].replace("$", "")
    formula_df = df.drop(columns=["__source_index"], errors="ignore")
    dependencies: set[tuple[int, str]] = set()

    aggregate_pattern = re.compile(
        r"\b(SUM|AVG|AVERAGE|MIN|MAX|COUNT|MEDIAN)\s*\(([^()]*)\)",
        flags=re.IGNORECASE,
    )
    for match in aggregate_pattern.finditer(expression):
        reference = match.group(2).strip()
        if reference in formula_df.columns:
            for position in range(len(df)):
                dependencies.add((_source_index_for_position(df, position), reference))
            continue

        whole_column_match = re.fullmatch(r"([A-Za-z]+):\1", reference)
        if whole_column_match:
            column = DataProcessor._column_from_letters(formula_df, whole_column_match.group(1))
            for position in range(len(df)):
                dependencies.add((_source_index_for_position(df, position), column))
            continue

        range_match = re.fullmatch(r"([A-Za-z]+)(\d+):([A-Za-z]+)(\d+)", reference)
        if range_match:
            start_letters, start_row, end_letters, end_row = range_match.groups()
            start_column_index = DataProcessor._letters_to_index(start_letters)
            end_column_index = DataProcessor._letters_to_index(end_letters)
            if start_column_index != end_column_index:
                raise ValueError("Formula ranges must stay within one column")
            column = DataProcessor._column_from_letters(formula_df, start_letters)
            start_position = int(start_row) - 1
            end_position = int(end_row) - 1
            if start_position < 0 or end_position < start_position:
                raise ValueError("Invalid formula row range")
            for position in range(start_position, min(end_position + 1, len(df))):
                dependencies.add((_source_index_for_position(df, position), column))

    for letters, row_number in re.findall(r"\b([A-Za-z]+)(\d+)\b", expression):
        column = DataProcessor._column_from_letters(formula_df, letters)
        position = int(row_number) - 1
        if position < 0 or position >= len(df):
            raise ValueError("Formula cell reference is outside dataset")
        dependencies.add((_source_index_for_position(df, position), column))

    return dependencies


def _assert_no_formula_cycle(
    db: Session,
    dataset: Dataset,
    df: pd.DataFrame,
    target_row_index: int,
    target_column: str,
    formula: str,
    skip_cell_id: Optional[int] = None,
) -> None:
    target = (target_row_index, target_column)
    formula_cells = (
        db.query(DatasetCell)
        .filter(DatasetCell.dataset_id == dataset.id, DatasetCell.formula.isnot(None))
        .all()
    )
    formulas: Dict[tuple[int, str], str] = {
        (cell.row_index, cell.column_name): cell.formula
        for cell in formula_cells
        if cell.formula and cell.id != skip_cell_id
    }
    formulas[target] = formula

    def dependencies_for(cell_key: tuple[int, str]) -> set[tuple[int, str]]:
        cell_formula = formulas.get(cell_key)
        if not cell_formula:
            return set()
        return _formula_dependency_cells(df, cell_formula)

    def reaches_target(cell_key: tuple[int, str], seen: set[tuple[int, str]]) -> bool:
        if cell_key == target:
            return True
        if cell_key in seen:
            return False
        seen.add(cell_key)
        return any(reaches_target(dependency, seen) for dependency in dependencies_for(cell_key))

    if any(reaches_target(dependency, set()) for dependency in dependencies_for(target)):
        raise ValueError("Formula creates a circular reference")


def _apply_sort(df: pd.DataFrame, sort: Optional[Dict[str, str]]) -> pd.DataFrame:
    if not sort:
        return df
    column = sort.get("column")
    direction = sort.get("direction", "asc")
    if column not in df.columns or column.startswith("__"):
        raise ValueError(f"Column '{column}' not found")
    return df.sort_values(
        by=column,
        ascending=direction != "desc",
        na_position="last",
        kind="mergesort",
    )


def _schema_by_name(dataset: Dataset) -> Dict[str, Dict[str, Any]]:
    return {
        column.get("name"): column
        for column in (dataset.schema or {}).get("columns", [])
    }


def _require_column(dataset: Dataset, column: Optional[str]) -> Dict[str, Any]:
    columns = _schema_by_name(dataset)
    if not column or column not in columns:
        raise ValueError(f"Column '{column}' not found")
    return columns[column]


def _row_value_expr(column: str):
    return DatasetRow.values_json[column].as_string()


def _typed_row_value_expr(dataset: Dataset, column: str):
    column_info = _require_column(dataset, column)
    expression = _row_value_expr(column)
    if column_info.get("semantic_type") == "numeric":
        return cast(expression, Float)
    return cast(expression, String)


def _coerce_sql_filter_value(dataset: Dataset, column: str, value: Any) -> Any:
    column_info = _require_column(dataset, column)
    if column_info.get("semantic_type") == "numeric":
        coerced = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
        if pd.isna(coerced):
            raise ValueError(f"Filter value for column '{column}' must be numeric")
        return float(coerced)
    return str(value)


def _filter_clause(dataset: Dataset, filter_item: Dict[str, Any]):
    column = filter_item["column"]
    operator_name = filter_item["operator"]
    value = filter_item["value"]
    expression = _typed_row_value_expr(dataset, column)

    if operator_name in {"eq", "ne", "gt", "lt", "gte", "lte"}:
        coerced = _coerce_sql_filter_value(dataset, column, value)
        if operator_name == "eq":
            return expression == coerced
        if operator_name == "ne":
            return expression != coerced
        if operator_name == "gt":
            return expression > coerced
        if operator_name == "lt":
            return expression < coerced
        if operator_name == "gte":
            return expression >= coerced
        if operator_name == "lte":
            return expression <= coerced

    text_expression = func.lower(cast(_row_value_expr(column), String))
    text_value = str(value).lower()
    if operator_name == "contains":
        return text_expression.contains(text_value)
    if operator_name == "startswith":
        return text_expression.startswith(text_value)
    if operator_name == "endswith":
        return text_expression.endswith(text_value)
    raise ValueError(f"Unknown filter operator: {operator_name}")


def _apply_sql_filters(row_query, dataset: Dataset, query: QuerySpec):
    if not query.filters:
        return row_query
    clauses = [_filter_clause(dataset, filter_item) for filter_item in query.filters]
    return row_query.filter(or_(*clauses) if query.logic == "or" else and_(*clauses))


def _filtered_row_query(
    db: Session,
    dataset: Dataset,
    filters: Optional[List[Dict[str, Any]]] = None,
    logic: str = "and",
):
    row_query = db.query(DatasetRow).filter(DatasetRow.dataset_id == dataset.id)
    if filters:
        row_query = _apply_sql_filters(
            row_query,
            dataset,
            QuerySpec(filters=filters, logic=logic),
        )
    return row_query


def _apply_sql_sort(row_query, dataset: Dataset, sort: Optional[Dict[str, str]]):
    if not sort:
        return row_query.order_by(DatasetRow.row_index.asc())
    column = sort.get("column")
    expression = _typed_row_value_expr(dataset, column)
    ordered = expression.desc() if sort.get("direction") == "desc" else expression.asc()
    return row_query.order_by(ordered, DatasetRow.row_index.asc())


def query_dataset(db: Session, dataset: Dataset, query: QuerySpec) -> Dict[str, Any]:
    ensure_db_storage(db, dataset)
    row_query = _filtered_row_query(db, dataset, query.filters, query.logic)
    total_rows = row_query.count()
    total_pages = (total_rows + query.page_size - 1) // query.page_size
    start_idx = (query.page - 1) * query.page_size
    rows = (
        _apply_sql_sort(row_query, dataset, query.sort)
        .offset(start_idx)
        .limit(query.page_size)
        .all()
    )
    page_source_indexes = [row.row_index for row in rows]
    page_records = _page_records_with_metadata(db, dataset, page_source_indexes)
    return {
        "data": page_records,
        "total_rows": total_rows,
        "page": query.page,
        "page_size": query.page_size,
        "total_pages": total_pages,
    }


def aggregate_dataset(
    db: Session,
    dataset: Dataset,
    column: str,
    operation: str,
    group_by: Optional[List[str]] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    logic: str = "and",
) -> Dict[str, Any]:
    ensure_db_storage(db, dataset)
    _require_column(dataset, column)
    if operation == "median":
        row_query = _filtered_row_query(db, dataset, filters, logic)
        filtered_count = row_query.count()
        if filtered_count == 0:
            return {"result": 0, "group_results": [] if group_by else None}
        if filtered_count > settings.MAX_FORMULA_EVAL_ROWS:
            raise ValueError(
                f"Median aggregation exceeds maximum of {settings.MAX_FORMULA_EVAL_ROWS} rows"
            )
        row_indexes = [
            row_index
            for (row_index,) in row_query.with_entities(DatasetRow.row_index).all()
        ]
        records = dataset_records(
            db,
            dataset,
            include_cell_metadata=False,
            row_indexes=row_indexes,
        )
        df = dataframe_from_records(records)
        return DataProcessor.aggregate(df, column, operation, group_by)

    expression = _typed_row_value_expr(dataset, column)
    if operation == "sum":
        aggregate_expression = func.sum(expression)
    elif operation == "avg":
        aggregate_expression = func.avg(expression)
    elif operation == "min":
        aggregate_expression = func.min(expression)
    elif operation == "max":
        aggregate_expression = func.max(expression)
    elif operation == "count":
        aggregate_expression = func.count(_row_value_expr(column))
    else:
        raise ValueError(f"Unknown operation: {operation}")

    row_query = _filtered_row_query(db, dataset, filters, logic)
    if group_by:
        group_expressions = []
        for group_column in group_by:
            _require_column(dataset, group_column)
            group_expressions.append(cast(_row_value_expr(group_column), String).label(group_column))
        rows = (
            row_query.with_entities(*group_expressions, aggregate_expression.label(column))
            .group_by(*group_expressions)
            .all()
        )
        group_results = []
        for row in rows:
            data = row._mapping
            group_results.append(
                {group_column: data[group_column] for group_column in group_by}
                | {column: data[column]}
            )
        return {"result": None, "group_results": group_results}

    result = row_query.with_entities(aggregate_expression).scalar()
    if result is None:
        result = 0
    return {
        "result": int(result) if operation == "count" else float(result),
        "group_results": None,
    }


def update_cell(
    db: Session,
    dataset: Dataset,
    row_index: int,
    column: str,
    value: Any,
    user_id: int,
    expected_version: Optional[int] = None,
    force: bool = False,
) -> Dict[str, Any]:
    ensure_db_storage(db, dataset)
    cell = (
        db.query(DatasetCell)
        .filter(
            DatasetCell.dataset_id == dataset.id,
            DatasetCell.row_index == row_index,
            DatasetCell.column_name == column,
        )
        .first()
    )
    if not cell:
        raise ValueError(f"Cell '{column}' row {row_index} not found")
    if expected_version is not None and not force and cell.version != expected_version:
        raise CellConflictError(row_index, column, cell.value, cell.version, value)

    records = _records_for_dataframe(db, dataset)
    df = dataframe_from_records(records)
    formula_df = df.drop(columns=["__source_index"], errors="ignore")
    formula = value.strip() if isinstance(value, str) and value.strip().startswith("=") else None
    if formula:
        _assert_no_formula_cycle(
            db,
            dataset,
            df,
            row_index,
            column,
            formula,
            skip_cell_id=cell.id,
        )
    stored_value = (
        DataProcessor.evaluate_formula(
            formula_df,
            formula,
            target_row_index=row_index,
            target_column=column,
        )
        if formula
        else value
    )

    cell.value = _json_safe(stored_value)
    cell.formula = formula
    cell.version = (cell.version or 0) + 1
    cell.updated_by_id = user_id
    row_values = dict(cell.row_ref.values_json or {})
    row_values[column] = cell.value
    cell.row_ref.values_json = row_values
    db.flush()

    recalculate_formulas(db, dataset, skip_cell_id=cell.id)
    db.flush()
    return {
        "row_index": row_index,
        "column": column,
        "value": cell.value,
        "formula": cell.formula,
        "version": cell.version,
    }


def recalculate_formulas(
    db: Session,
    dataset: Dataset,
    skip_cell_id: Optional[int] = None,
) -> None:
    formula_cells = (
        db.query(DatasetCell)
        .filter(DatasetCell.dataset_id == dataset.id, DatasetCell.formula.isnot(None))
        .all()
    )
    if not formula_cells:
        return
    records = _records_for_dataframe(db, dataset)
    df = dataframe_from_records(records)
    formula_df = df.drop(columns=["__source_index"], errors="ignore")
    for cell in formula_cells:
        if skip_cell_id and cell.id == skip_cell_id:
            continue
        try:
            new_value = DataProcessor.evaluate_formula(
                formula_df,
                cell.formula,
                target_row_index=cell.row_index,
                target_column=cell.column_name,
            )
        except ValueError:
            continue
        if cell.value != new_value:
            cell.value = _json_safe(new_value)
            cell.version = (cell.version or 0) + 1
            row_values = dict(cell.row_ref.values_json or {})
            row_values[cell.column_name] = cell.value
            cell.row_ref.values_json = row_values


def full_records_for_export(
    db: Session,
    dataset: Dataset,
    filters: List[Dict[str, Any]],
    logic: str,
    sort: Optional[Dict[str, str]],
) -> List[Dict[str, Any]]:
    ensure_db_storage(db, dataset)
    row_query = _filtered_row_query(db, dataset, filters, logic)
    row_indexes = [
        row_index
        for (row_index,) in row_query.with_entities(DatasetRow.row_index).all()
    ]
    records = dataset_records(
        db,
        dataset,
        include_cell_metadata=False,
        row_indexes=row_indexes,
    )
    if not records:
        return []
    df = dataframe_from_records(records)
    df = _apply_sort(df, sort)
    return [
        {key: value for key, value in row.items() if not key.startswith("__")}
        for row in df.to_dict(orient="records")
    ]


def count_records_for_export(
    db: Session,
    dataset: Dataset,
    filters: List[Dict[str, Any]],
    logic: str,
) -> int:
    ensure_db_storage(db, dataset)
    return _filtered_row_query(db, dataset, filters, logic).count()
