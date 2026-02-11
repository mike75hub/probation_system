"""
Data processing utilities for datasets.
"""
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime
from django.conf import settings

class DatasetProcessor:
    """Process uploaded datasets."""
    
    @staticmethod
    def process_uploaded_file(file_path, file_format):
        """Process uploaded file and extract basic information."""
        try:
            if file_format == 'csv':
                df = pd.read_csv(file_path)
            elif file_format in ['xlsx', 'xls']:
                df = pd.read_excel(file_path)
            elif file_format == 'json':
                df = pd.read_json(file_path)
            elif file_format == 'parquet':
                df = pd.read_parquet(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_format}")
            
            return {
                'row_count': len(df),
                'column_count': len(df.columns),
                'column_names': df.columns.tolist(),
                'dtypes': df.dtypes.astype(str).to_dict(),
                'sample_data': df.head(5).to_dict('records')
            }
        except Exception as e:
            raise Exception(f"Error processing file: {str(e)}")
    
    @staticmethod
    def clean_dataset(dataset):
        """Clean and preprocess dataset."""
        try:
            file_path = dataset.original_file.path
            file_format = dataset.file_format.lower()
            
            # Read data
            if file_format == 'csv':
                df = pd.read_csv(file_path)
            elif file_format in ['xlsx', 'xls']:
                df = pd.read_excel(file_path)
            else:
                raise ValueError(f"Unsupported format for cleaning: {file_format}")
            
            # Basic cleaning
            df_clean = df.copy()
            
            # Remove duplicate rows
            initial_rows = len(df_clean)
            df_clean = df_clean.drop_duplicates()
            duplicates_removed = initial_rows - len(df_clean)
            
            # Handle missing values
            missing_stats = df_clean.isnull().sum().to_dict()
            
            # For numerical columns, fill with median
            numerical_cols = df_clean.select_dtypes(include=[np.number]).columns
            for col in numerical_cols:
                if df_clean[col].isnull().any():
                    df_clean[col].fillna(df_clean[col].median(), inplace=True)
            
            # For categorical columns, fill with mode
            categorical_cols = df_clean.select_dtypes(include=['object']).columns
            for col in categorical_cols:
                if df_clean[col].isnull().any():
                    df_clean[col].fillna(df_clean[col].mode()[0], inplace=True)
            
            # Save cleaned dataset
            processed_dir = os.path.join(settings.MEDIA_ROOT, 'datasets/processed', 
                                        datetime.now().strftime('%Y/%m/%d'))
            os.makedirs(processed_dir, exist_ok=True)
            
            processed_file_name = f"cleaned_{os.path.basename(file_path)}"
            processed_file_path = os.path.join(processed_dir, processed_file_name)
            
            if file_format == 'csv':
                df_clean.to_csv(processed_file_path, index=False)
            elif file_format in ['xlsx', 'xls']:
                df_clean.to_excel(processed_file_path, index=False)
            
            return {
                'processed_file_path': processed_file_path,
                'duplicates_removed': duplicates_removed,
                'missing_values_handled': missing_stats,
                'cleaned_rows': len(df_clean),
                'cleaned_columns': len(df_clean.columns)
            }
            
        except Exception as e:
            raise Exception(f"Error cleaning dataset: {str(e)}")
    
    @staticmethod
    def validate_dataset_structure(df, required_columns=None, column_types=None):
        """Validate dataset structure."""
        validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check required columns
        if required_columns:
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                validation_results['is_valid'] = False
                validation_results['errors'].append(f"Missing required columns: {missing_columns}")
        
        # Check column types
        if column_types:
            for col, expected_type in column_types.items():
                if col in df.columns:
                    actual_type = str(df[col].dtype)
                    if expected_type != actual_type:
                        validation_results['warnings'].append(
                            f"Column '{col}' has type {actual_type}, expected {expected_type}"
                        )
        
        # Check for missing values
        missing_values = df.isnull().sum()
        if missing_values.sum() > 0:
            validation_results['warnings'].append(
                f"Dataset contains {missing_values.sum()} missing values"
            )
        
        return validation_results
    
    @staticmethod
    def split_dataset(file_path, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15):
        """Split dataset into train, validation, and test sets."""
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
            else:
                raise ValueError("Unsupported file format")
            
            # Shuffle the dataset
            df = df.sample(frac=1, random_state=42).reset_index(drop=True)
            
            # Calculate split indices
            n = len(df)
            train_end = int(n * train_ratio)
            val_end = train_end + int(n * val_ratio)
            
            # Split the data
            train_df = df.iloc[:train_end]
            val_df = df.iloc[train_end:val_end]
            test_df = df.iloc[val_end:]
            
            return train_df, val_df, test_df
            
        except Exception as e:
            raise Exception(f"Error splitting dataset: {str(e)}")