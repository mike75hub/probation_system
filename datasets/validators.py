"""
Dataset validation utilities.
"""
import csv
import os
from pathlib import Path

import pandas as pd
import numpy as np
from django.core.exceptions import ValidationError

class DatasetValidator:
    """Validate uploaded datasets."""
    
    @staticmethod
    def validate_file_extension(value):
        """Validate file extension."""
        allowed_extensions = ['csv', 'xlsx', 'xls', 'json', 'parquet']
        ext = value.name.split('.')[-1].lower()
        if ext not in allowed_extensions:
            raise ValidationError(
                f'Unsupported file extension. Allowed: {", ".join(allowed_extensions)}'
            )
    
    @staticmethod
    def validate_file_size(value, max_size_mb=100):
        """Validate file size."""
        max_size_bytes = max_size_mb * 1024 * 1024
        if value.size > max_size_bytes:
            raise ValidationError(f'File size exceeds {max_size_mb}MB limit')
    
    @staticmethod
    def validate_csv_structure(file_path):
        """Validate CSV file structure.

        Accepts a filesystem path, a Django UploadedFile, or any file-like object.
        """
        try:
            # Prefer a real path if available (e.g. TemporaryUploadedFile).
            tmp_path_fn = getattr(file_path, "temporary_file_path", None)
            if callable(tmp_path_fn):
                file_path = tmp_path_fn()

            if isinstance(file_path, (str, os.PathLike, Path)):
                with open(file_path, "r", encoding="utf-8-sig", errors="replace", newline="") as fp:
                    return DatasetValidator._validate_csv_fp(fp)

            fp = getattr(file_path, "file", file_path)
            pos = None
            try:
                if hasattr(fp, "tell") and hasattr(fp, "seek"):
                    pos = fp.tell()
                    fp.seek(0)

                return DatasetValidator._validate_csv_fp(fp)
            finally:
                if pos is not None and hasattr(fp, "seek"):
                    fp.seek(pos)

        except (UnicodeDecodeError, csv.Error) as e:
            raise ValidationError(f"CSV parsing error: {str(e)}")
        except Exception as e:
            raise ValidationError(f"Error validating CSV: {str(e)}")

    @staticmethod
    def _validate_csv_fp(fp):
        # Read header line
        header_line = fp.readline()
        if isinstance(header_line, (bytes, bytearray)):
            header_line = header_line.decode("utf-8-sig", errors="replace")

        if not header_line or not header_line.strip():
            raise ValidationError("CSV file is empty")

        try:
            header = next(csv.reader([header_line]))
        except csv.Error as e:
            raise ValidationError(f"CSV parsing error: {str(e)}")

        if not header:
            raise ValidationError("CSV file is empty")

        if any((col or "").strip() == "" for col in header):
            raise ValidationError("CSV contains empty column names")

        # Ensure there's at least one non-empty data row after the header.
        for _ in range(50):
            line = fp.readline()
            if not line:
                break
            if isinstance(line, (bytes, bytearray)):
                line = line.decode("utf-8", errors="replace")
            if line.strip():
                # There is data (not just header)
                return True

        raise ValidationError("CSV file is empty")
    
    @staticmethod
    def validate_data_types(df, column_specifications):
        """Validate data types of columns."""
        errors = []
        
        for column, expected_type in column_specifications.items():
            if column not in df.columns:
                errors.append(f"Column '{column}' not found")
                continue
            
            if expected_type == 'numeric':
                if not np.issubdtype(df[column].dtype, np.number):
                    errors.append(f"Column '{column}' should be numeric")
            elif expected_type == 'categorical':
                if df[column].dtype != 'object':
                    errors.append(f"Column '{column}' should be categorical")
            elif expected_type == 'date':
                try:
                    pd.to_datetime(df[column])
                except:
                    errors.append(f"Column '{column}' should contain valid dates")
        
        if errors:
            raise ValidationError("; ".join(errors))
    
    @staticmethod
    def check_for_sensitive_data(df):
        """Check for potentially sensitive data."""
        sensitive_keywords = [
            'password', 'ssn', 'social', 'credit', 'card', 'bank', 
            'account', 'pin', 'security', 'secret', 'token'
        ]
        
        warnings = []
        columns_lower = [col.lower() for col in df.columns]
        
        for keyword in sensitive_keywords:
            for col in columns_lower:
                if keyword in col:
                    warnings.append(f"Column may contain sensitive data: {keyword}")
                    break
        
        return warnings
