import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import re


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
    def evaluate_formula(df: pd.DataFrame, formula: str) -> Any:
        """Evaluate a small set of spreadsheet-like aggregate formulas."""
        expression = formula.strip()
        if not expression.startswith("="):
            return formula

        expression = expression[1:].strip()
        if "(" not in expression or not expression.endswith(")"):
            raise ValueError("Unsupported formula")

        operation, reference = expression[:-1].split("(", 1)
        operation = operation.strip().lower()
        reference = reference.strip()

        series = DataProcessor._formula_series(df, reference)
        numeric_series = pd.to_numeric(series, errors="coerce")

        if operation == "sum":
            return float(numeric_series.sum())
        if operation in {"avg", "average"}:
            return float(numeric_series.mean())
        if operation == "min":
            return float(numeric_series.min())
        if operation == "max":
            return float(numeric_series.max())
        if operation == "count":
            return int(series.count())
        if operation == "median":
            return float(numeric_series.median())

        raise ValueError(f"Unknown formula: {operation}")

    @staticmethod
    def _formula_series(df: pd.DataFrame, reference: str) -> pd.Series:
        """Resolve a formula reference to a Series.

        Supports existing column names, whole-column references such as B:B,
        and one-based A1 ranges such as A1:A5.
        """
        if reference in df.columns:
            return df[reference]

        whole_column_match = re.fullmatch(
            r"([A-Za-z]+):\1",
            reference.replace("$", ""),
        )
        if whole_column_match:
            column = DataProcessor._column_from_letters(df, whole_column_match.group(1))
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
            DataProcessor.evaluate_formula(df, value)
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
                mask = df[column].astype(str).str.contains(str(value), case=False, na=False)
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
