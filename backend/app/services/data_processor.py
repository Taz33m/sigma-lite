import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from pathlib import Path
import json


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
        
        page_data = df.iloc[start_idx:end_idx]
        
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
                continue
            
            if operator == "eq":
                mask = df[column] == value
            elif operator == "ne":
                mask = df[column] != value
            elif operator == "gt":
                mask = df[column] > value
            elif operator == "lt":
                mask = df[column] < value
            elif operator == "gte":
                mask = df[column] >= value
            elif operator == "lte":
                mask = df[column] <= value
            elif operator == "contains":
                mask = df[column].astype(str).str.contains(str(value), case=False, na=False)
            elif operator == "startswith":
                mask = df[column].astype(str).str.startswith(str(value), na=False)
            elif operator == "endswith":
                mask = df[column].astype(str).str.endswith(str(value), na=False)
            else:
                continue
            
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
