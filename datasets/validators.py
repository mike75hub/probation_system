"""
Dataset validation utilities.
"""
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
        """Validate CSV file structure."""
        try:
            # Try to read the CSV file
            df = pd.read_csv(file_path, nrows=5)
            
            # Check if dataframe is not empty
            if df.empty:
                raise ValidationError("CSV file is empty")
            
            # Check for valid column names
            if any(col.strip() == '' for col in df.columns):
                raise ValidationError("CSV contains empty column names")
            
            return True
            
        except pd.errors.EmptyDataError:
            raise ValidationError("CSV file is empty")
        except pd.errors.ParserError as e:
            raise ValidationError(f"CSV parsing error: {str(e)}")
        except Exception as e:
            raise ValidationError(f"Error validating CSV: {str(e)}")
    
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