import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import ast
import math
import operator
import re

from app.core.config import settings


class DataProcessor:
    """Service for processing and analyzing datasets."""
    
    @staticmethod
    def read_csv(file_path: str) -> pd.DataFrame:
        """Read CSV file into DataFrame."""
        return pd.read_csv(file_path)
    
    @staticmethod
    def infer_schema(df: pd.DataFrame) -> Dict[str, Any]:
        """Infer schema from DataFrame."""
        schema = {
            "columns": [],
            "row_count": len(df),
            "column_count": len(df.columns)
        }
        
        for col in df.columns:
            col_info = {
                "name": col,
                "type": str(df[col].dtype),
                "nullable": bool(df[col].isnull().any()),
                "unique_count": int(df[col].nunique()),
                "sample_values": df[col].dropna().head(5).tolist()
            }
            
            # Detect semantic type
            if pd.api.types.is_numeric_dtype(df[col]):
                col_info["semantic_type"] = "numeric"
                col_info["min"] = float(df[col].min()) if not df[col].isnull().all() else None
                col_info["max"] = float(df[col].max()) if not df[col].isnull().all() else None
                col_info["mean"] = float(df[col].mean()) if not df[col].isnull().all() else None
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                col_info["semantic_type"] = "datetime"
            else:
                col_info["semantic_type"] = "text"
            
            schema["columns"].append(col_info)
        
        return schema
    
    @staticmethod
    def get_data_page(
        df: pd.DataFrame,
        page: int = 1,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """Get paginated data from DataFrame."""
        total_rows = len(df)
        total_pages = (total_rows + page_size - 1) // page_size
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        page_data = df.iloc[start_idx:end_idx].copy()
        page_data["__source_index"] = page_data.index
        
        # Convert to list of dicts, handling NaN values
        data = json.loads(page_data.to_json(orient='records', date_format='iso'))
        
        return {
            "data": data,
            "total_rows": total_rows,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

    @staticmethod
    def evaluate_formula(
        df: pd.DataFrame,
        formula: str,
        target_row_index: Optional[int] = None,
        target_column: Optional[str] = None,
    ) -> Any:
        """Evaluate a small set of spreadsheet-like aggregate formulas."""
        expression = formula.strip()
        if not expression.startswith("="):
            return formula
        if len(expression) > settings.MAX_FORMULA_LENGTH:
            raise ValueError("Formula exceeds maximum length")
        if len(df) > settings.MAX_FORMULA_EVAL_ROWS:
            raise ValueError("Formula evaluation exceeds maximum row count")

        expression = expression[1:].strip()
        if not expression:
            raise ValueError("Unsupported formula")

        expression = DataProcessor._replace_aggregate_calls(
            df,
            expression,
            target_row_index=target_row_index,
            target_column=target_column,
        )
        expression = DataProcessor._replace_cell_references(
            df,
            expression,
            target_row_index=target_row_index,
            target_column=target_column,
        )

        return DataProcessor._safe_arithmetic_eval(expression)

    @staticmethod
    def _replace_aggregate_calls(
        df: pd.DataFrame,
        expression: str,
        target_row_index: Optional[int] = None,
        target_column: Optional[str] = None,
    ) -> str:
        pattern = re.compile(
            r"\b(SUM|AVG|AVERAGE|MIN|MAX|COUNT|MEDIAN)\s*\(([^()]*)\)",
            flags=re.IGNORECASE,
        )

        def replace(match: re.Match) -> str:
            operation = match.group(1).lower()
            reference = match.group(2).strip()
            series = DataProcessor._formula_series(
                df,
                reference,
                target_row_index=target_row_index,
                target_column=target_column,
            )
            numeric_series = pd.to_numeric(series, errors="coerce")

            if operation == "sum":
                value = numeric_series.sum()
            elif operation in {"avg", "average"}:
                value = numeric_series.mean()
            elif operation == "min":
                value = numeric_series.min()
            elif operation == "max":
                value = numeric_series.max()
            elif operation == "count":
                value = series.count()
            elif operation == "median":
                value = numeric_series.median()
            else:
                raise ValueError(f"Unknown formula: {operation}")

            if pd.isna(value):
                return "0"
            return repr(float(value) if operation != "count" else int(value))

        previous = None
        current = expression
        while previous != current:
            previous = current
            current = pattern.sub(replace, current)
        return current

    @staticmethod
    def _replace_cell_references(
        df: pd.DataFrame,
        expression: str,
        target_row_index: Optional[int] = None,
        target_column: Optional[str] = None,
    ) -> str:
        whole_column_or_range = re.compile(
            r"([A-Za-z]+):\1|([A-Za-z]+)\d+:([A-Za-z]+)\d+"
        )
        if whole_column_or_range.search(expression):
            raise ValueError("Ranges must be used inside aggregate functions")

        def replace(match: re.Match) -> str:
            letters, row_number = match.groups()
            column = DataProcessor._column_from_letters(df, letters)
            row_index = int(row_number) - 1
            if row_index < 0 or row_index >= len(df):
                raise ValueError("Formula cell reference is outside dataset")
            if target_row_index == row_index and target_column == column:
                raise ValueError("Formula cannot reference its own cell")

            value = df.iloc[row_index][column]
            numeric_value = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
            if pd.isna(numeric_value):
                return "0"
            return repr(float(numeric_value))

        return re.sub(r"\b([A-Za-z]+)(\d+)\b", replace, expression)

    @staticmethod
    def _safe_arithmetic_eval(expression: str) -> Any:
        allowed_binops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Mod: operator.mod,
        }
        allowed_unary = {ast.UAdd: operator.pos, ast.USub: operator.neg}

        def checked_number(value: float) -> float:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("Unsupported formula")
            if not math.isfinite(float(value)) or abs(float(value)) > 1_000_000_000_000:
                raise ValueError("Formula result is outside supported numeric range")
            return value

        def evaluate(node: ast.AST) -> float:
            if isinstance(node, ast.Expression):
                return evaluate(node.body)
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return checked_number(node.value)
            if isinstance(node, ast.BinOp) and type(node.op) in allowed_binops:
                return checked_number(allowed_binops[type(node.op)](evaluate(node.left), evaluate(node.right)))
            if isinstance(node, ast.UnaryOp) and type(node.op) in allowed_unary:
                return checked_number(allowed_unary[type(node.op)](evaluate(node.operand)))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                function = node.func.id.lower()
                if function == "round":
                    args = [evaluate(arg) for arg in node.args]
                    if len(args) not in {1, 2}:
                        raise ValueError("ROUND expects one or two arguments")
                    return checked_number(round(args[0], int(args[1]) if len(args) == 2 else 0))
            raise ValueError("Unsupported formula")

        try:
            tree = ast.parse(expression, mode="eval")
            if sum(1 for _ in ast.walk(tree)) > 64:
                raise ValueError("Formula is too complex")
            result = evaluate(tree)
        except ZeroDivisionError as exc:
            raise ValueError("Formula division by zero") from exc
        except SyntaxError as exc:
            raise ValueError("Unsupported formula") from exc

        if isinstance(result, float) and result.is_integer():
            return int(result)
        return result

    @staticmethod
    def _formula_series(
        df: pd.DataFrame,
        reference: str,
        target_row_index: Optional[int] = None,
        target_column: Optional[str] = None,
    ) -> pd.Series:
        """Resolve a formula reference to a Series.

        Supports existing column names, whole-column references such as B:B,
        and one-based A1 ranges such as A1:A5.
        """
        if reference in df.columns:
            if target_column == reference:
                raise ValueError("Formula cannot reference its own cell")
            return df[reference]

        whole_column_match = re.fullmatch(
            r"([A-Za-z]+):\1",
            reference.replace("$", ""),
        )
        if whole_column_match:
            column = DataProcessor._column_from_letters(df, whole_column_match.group(1))
            if target_column == column:
                raise ValueError("Formula cannot reference its own cell")
            return df[column]

        range_match = re.fullmatch(
            r"([A-Za-z]+)(\d+):([A-Za-z]+)(\d+)",
            reference.replace("$", ""),
        )
        if range_match:
            start_letters, start_row, end_letters, end_row = range_match.groups()
            start_column_index = DataProcessor._letters_to_index(start_letters)
            end_column_index = DataProcessor._letters_to_index(end_letters)
            if start_column_index != end_column_index:
                raise ValueError("Formula ranges must stay within one column")

            column = DataProcessor._column_from_letters(df, start_letters)
            start_index = int(start_row) - 1
            end_index = int(end_row) - 1
            if start_index < 0 or end_index < start_index:
                raise ValueError("Invalid formula row range")
            if start_index >= len(df):
                raise ValueError("Formula row range starts outside dataset")
            if (
                target_column == column
                and target_row_index is not None
                and start_index <= target_row_index <= end_index
            ):
                raise ValueError("Formula cannot reference its own cell")

            return df[column].iloc[start_index : min(end_index + 1, len(df))]

        raise ValueError(f"Column or range '{reference}' not found")

    @staticmethod
    def _column_from_letters(df: pd.DataFrame, letters: str) -> str:
        column_index = DataProcessor._letters_to_index(letters)
        if column_index < 0 or column_index >= len(df.columns):
            raise ValueError(f"Column '{letters}' not found")
        return str(df.columns[column_index])

    @staticmethod
    def _letters_to_index(letters: str) -> int:
        index = 0
        for char in letters.upper():
            if not "A" <= char <= "Z":
                raise ValueError(f"Invalid column reference '{letters}'")
            index = index * 26 + (ord(char) - ord("A") + 1)
        return index - 1

    @staticmethod
    def update_cell(
        df: pd.DataFrame,
        row_index: int,
        column: str,
        value: Any
    ) -> tuple[pd.DataFrame, Any]:
        """Update one cell by source row index and return the stored value."""
        if row_index < 0 or row_index >= len(df):
            raise ValueError("Row index out of range")
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found")

        stored_value = (
            DataProcessor.evaluate_formula(
                df,
                value,
                target_row_index=row_index,
                target_column=column,
            )
            if isinstance(value, str) and value.strip().startswith("=")
            else value
        )
        df.at[row_index, column] = stored_value
        return df, stored_value
    
    @staticmethod
    def apply_filters(
        df: pd.DataFrame,
        filters: List[Dict[str, Any]],
        logic: str = "and"
    ) -> pd.DataFrame:
        """Apply filters to DataFrame."""
        if not filters:
            return df
        
        masks = []
        
        for f in filters:
            column = f["column"]
            operator = f["operator"]
            value = f["value"]
            
            if column not in df.columns:
                raise ValueError(f"Column '{column}' not found")
            
            if operator == "eq":
                mask = df[column] == DataProcessor._coerce_filter_value(
                    df[column], value, column
                )
            elif operator == "ne":
                mask = df[column] != DataProcessor._coerce_filter_value(
                    df[column], value, column
                )
            elif operator == "gt":
                mask = df[column] > DataProcessor._coerce_filter_value(
                    df[column], value, column
                )
            elif operator == "lt":
                mask = df[column] < DataProcessor._coerce_filter_value(
                    df[column], value, column
                )
            elif operator == "gte":
                mask = df[column] >= DataProcessor._coerce_filter_value(
                    df[column], value, column
                )
            elif operator == "lte":
                mask = df[column] <= DataProcessor._coerce_filter_value(
                    df[column], value, column
                )
            elif operator == "contains":
                mask = df[column].astype(str).str.contains(str(value), case=False, na=False, regex=False)
            elif operator == "startswith":
                mask = df[column].astype(str).str.startswith(str(value), na=False)
            elif operator == "endswith":
                mask = df[column].astype(str).str.endswith(str(value), na=False)
            else:
                raise ValueError(f"Unknown filter operator: {operator}")
            
            masks.append(mask)
        
        if not masks:
            return df
        
        # Combine masks
        if logic == "and":
            combined_mask = masks[0]
            for mask in masks[1:]:
                combined_mask &= mask
        else:  # or
            combined_mask = masks[0]
            for mask in masks[1:]:
                combined_mask |= mask
        
        return df[combined_mask]

    @staticmethod
    def _coerce_filter_value(series: pd.Series, value: Any, column: str) -> Any:
        """Coerce exact/comparison filter values to the target column type."""
        if pd.api.types.is_numeric_dtype(series):
            coerced = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
            if pd.isna(coerced):
                raise ValueError(f"Filter value for column '{column}' must be numeric")
            return coerced

        if pd.api.types.is_datetime64_any_dtype(series):
            coerced = pd.to_datetime(pd.Series([value]), errors="coerce").iloc[0]
            if pd.isna(coerced):
                raise ValueError(f"Filter value for column '{column}' must be a date")
            return coerced

        return value
    
    @staticmethod
    def aggregate(
        df: pd.DataFrame,
        column: str,
        operation: str,
        group_by: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Perform aggregation on DataFrame."""
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found")
        
        result = {"result": None, "group_results": None}
        
        if group_by:
            # Group aggregation
            valid_groups = [g for g in group_by if g in df.columns]
            if not valid_groups:
                raise ValueError("No valid group by columns")
            
            grouped = df.groupby(valid_groups)[column]
            
            if operation == "sum":
                agg_result = grouped.sum()
            elif operation == "avg":
                agg_result = grouped.mean()
            elif operation == "min":
                agg_result = grouped.min()
            elif operation == "max":
                agg_result = grouped.max()
            elif operation == "count":
                agg_result = grouped.count()
            elif operation == "median":
                agg_result = grouped.median()
            else:
                raise ValueError(f"Unknown operation: {operation}")
            
            # Convert to list of dicts
            result["group_results"] = json.loads(
                agg_result.reset_index().to_json(orient='records')
            )
        else:
            # Simple aggregation
            if operation == "sum":
                result["result"] = float(df[column].sum())
            elif operation == "avg":
                result["result"] = float(df[column].mean())
            elif operation == "min":
                result["result"] = float(df[column].min())
            elif operation == "max":
                result["result"] = float(df[column].max())
            elif operation == "count":
                result["result"] = int(df[column].count())
            elif operation == "median":
                result["result"] = float(df[column].median())
            else:
                raise ValueError(f"Unknown operation: {operation}")
        
        return result
    
    @staticmethod
    def get_column_stats(df: pd.DataFrame, column: str) -> Dict[str, Any]:
        """Get statistics for a column."""
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found")
        
        col_data = df[column]
        stats = {
            "column": column,
            "count": int(col_data.count()),
            "null_count": int(col_data.isnull().sum()),
            "unique_count": int(col_data.nunique())
        }
        
        if pd.api.types.is_numeric_dtype(col_data):
            stats.update({
                "mean": float(col_data.mean()),
                "median": float(col_data.median()),
                "std": float(col_data.std()),
                "min": float(col_data.min()),
                "max": float(col_data.max()),
                "q25": float(col_data.quantile(0.25)),
                "q75": float(col_data.quantile(0.75))
            })
        
        return stats
