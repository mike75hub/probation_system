"""
ML model training utilities.
"""
import os
import pickle
import json
import time
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, mean_squared_error,
    r2_score, roc_auc_score, mean_absolute_error
)
import joblib

class ModelTrainer:
    """Train ML models for probation system."""
    
    def __init__(self):
        self.models = {
            'logistic_regression': self._train_logistic_regression,
            'random_forest': self._train_random_forest,
            'decision_tree': self._train_decision_tree,
            'xgboost': self._train_xgboost,
            'svm': self._train_svm
        }
    
    def train_model(self, algorithm, X_train, y_train, X_val=None, y_val=None, **params):
        """Train a model with the specified algorithm."""
        if algorithm not in self.models:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        trainer_func = self.models[algorithm]
        return trainer_func(X_train, y_train, X_val, y_val, **params)

    def _resolve_problem_type(self, y_train, model_type=None):
        """Resolve whether training should be classification or regression."""
        if model_type in ('classification', 'regression'):
            return model_type == 'classification'
        return len(np.unique(y_train)) < 10
    
    def _train_logistic_regression(self, X_train, y_train, X_val=None, y_val=None, **params):
        """Train Logistic Regression model."""
        from sklearn.linear_model import LogisticRegression

        model_type = params.get('model_type')
        if model_type == 'regression':
            raise ValueError("Logistic Regression is only valid for classification model type.")
        
        model = LogisticRegression(
            C=params.get('C', 1.0),
            max_iter=params.get('max_iter', 100),
            random_state=42,
            solver=params.get('solver', 'lbfgs')
        )
        
        start_time = time.time()
        model.fit(X_train, y_train)
        training_time = time.time() - start_time
        
        return {
            'model': model,
            'training_time': training_time,
            'algorithm': 'logistic_regression',
            'parameters': model.get_params()
        }
    
    def _train_random_forest(self, X_train, y_train, X_val=None, y_val=None, **params):
        """Train Random Forest model."""
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
        
        is_classification = self._resolve_problem_type(y_train, params.get('model_type'))
        
        if is_classification:
            model = RandomForestClassifier(
                n_estimators=params.get('n_estimators', 100),
                max_depth=params.get('max_depth', None),
                min_samples_split=params.get('min_samples_split', 2),
                min_samples_leaf=params.get('min_samples_leaf', 1),
                random_state=42
            )
        else:
            model = RandomForestRegressor(
                n_estimators=params.get('n_estimators', 100),
                max_depth=params.get('max_depth', None),
                min_samples_split=params.get('min_samples_split', 2),
                min_samples_leaf=params.get('min_samples_leaf', 1),
                random_state=42
            )
        
        start_time = time.time()
        model.fit(X_train, y_train)
        training_time = time.time() - start_time
        
        # Get feature importance
        feature_importance = dict(zip(range(len(X_train.columns)), model.feature_importances_))
        
        return {
            'model': model,
            'training_time': training_time,
            'algorithm': 'random_forest',
            'feature_importance': feature_importance,
            'parameters': model.get_params()
        }
    
    def _train_decision_tree(self, X_train, y_train, X_val=None, y_val=None, **params):
        """Train Decision Tree model."""
        from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
        
        is_classification = self._resolve_problem_type(y_train, params.get('model_type'))
        
        if is_classification:
            model = DecisionTreeClassifier(
                max_depth=params.get('max_depth', None),
                min_samples_split=params.get('min_samples_split', 2),
                min_samples_leaf=params.get('min_samples_leaf', 1),
                random_state=42
            )
        else:
            model = DecisionTreeRegressor(
                max_depth=params.get('max_depth', None),
                min_samples_split=params.get('min_samples_split', 2),
                min_samples_leaf=params.get('min_samples_leaf', 1),
                random_state=42
            )
        
        start_time = time.time()
        model.fit(X_train, y_train)
        training_time = time.time() - start_time
        
        return {
            'model': model,
            'training_time': training_time,
            'algorithm': 'decision_tree',
            'parameters': model.get_params()
        }
    
    def _train_xgboost(self, X_train, y_train, X_val=None, y_val=None, **params):
        """Train XGBoost model."""
        try:
            import xgboost as xgb
        except ImportError:
            raise ImportError("XGBoost is not installed. Install it with: pip install xgboost")
        
        is_classification = self._resolve_problem_type(y_train, params.get('model_type'))
        
        if is_classification:
            model = xgb.XGBClassifier(
                n_estimators=params.get('n_estimators', 100),
                max_depth=params.get('max_depth', 3),
                learning_rate=params.get('learning_rate', 0.1),
                random_state=42
            )
        else:
            model = xgb.XGBRegressor(
                n_estimators=params.get('n_estimators', 100),
                max_depth=params.get('max_depth', 3),
                learning_rate=params.get('learning_rate', 0.1),
                random_state=42
            )
        
        start_time = time.time()
        
        if X_val is not None and y_val is not None:
            model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                verbose=False
            )
        else:
            model.fit(X_train, y_train)
        
        training_time = time.time() - start_time
        
        # Get feature importance
        feature_importance = dict(zip(range(len(X_train.columns)), model.feature_importances_))
        
        return {
            'model': model,
            'training_time': training_time,
            'algorithm': 'xgboost',
            'feature_importance': feature_importance,
            'parameters': model.get_params()
        }
    
    def _train_svm(self, X_train, y_train, X_val=None, y_val=None, **params):
        """Train Support Vector Machine model."""
        from sklearn.svm import SVC, SVR
        
        is_classification = self._resolve_problem_type(y_train, params.get('model_type'))
        
        if is_classification:
            model = SVC(
                C=params.get('C', 1.0),
                kernel=params.get('kernel', 'rbf'),
                probability=True,
                random_state=42
            )
        else:
            model = SVR(
                C=params.get('C', 1.0),
                kernel=params.get('kernel', 'rbf')
            )
        
        start_time = time.time()
        model.fit(X_train, y_train)
        training_time = time.time() - start_time
        
        return {
            'model': model,
            'training_time': training_time,
            'algorithm': 'svm',
            'parameters': model.get_params()
        }
    
    def evaluate_model(self, model, X_test, y_test, model_type='classification'):
        """Evaluate model performance."""
        predictions = model.predict(X_test)
        
        if model_type == 'classification':
            metrics = {
                'accuracy': accuracy_score(y_test, predictions),
                'precision': precision_score(y_test, predictions, average='weighted', zero_division=0),
                'recall': recall_score(y_test, predictions, average='weighted', zero_division=0),
                'f1_score': f1_score(y_test, predictions, average='weighted', zero_division=0)
            }
            
            # Confusion matrix
            cm = confusion_matrix(y_test, predictions)
            metrics['confusion_matrix'] = cm.tolist()
            
            # Classification report
            report = classification_report(y_test, predictions, output_dict=True, zero_division=0)
            metrics['classification_report'] = report
            
            # AUC-ROC for binary classification
            if len(np.unique(y_test)) == 2:
                try:
                    prob_predictions = model.predict_proba(X_test)[:, 1]
                    metrics['auc_roc'] = roc_auc_score(y_test, prob_predictions)
                except:
                    metrics['auc_roc'] = None
            
        else:  # regression
            metrics = {
                'mse': mean_squared_error(y_test, predictions),
                'rmse': np.sqrt(mean_squared_error(y_test, predictions)),
                'mae': mean_absolute_error(y_test, predictions),
                'r2_score': r2_score(y_test, predictions)
            }
        
        return metrics
    
    def save_model(self, model_result, save_path, scaler=None, encoder=None):
        """Save trained model and associated files."""
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # Save model
        with open(save_path, 'wb') as f:
            pickle.dump(model_result['model'], f)
        
        # Save scaler if provided
        scaler_path = None
        if scaler:
            scaler_path = save_path.replace('.pkl', '_scaler.pkl')
            with open(scaler_path, 'wb') as f:
                pickle.dump(scaler, f)
        
        # Save encoder if provided
        encoder_path = None
        if encoder:
            encoder_path = save_path.replace('.pkl', '_encoder.pkl')
            with open(encoder_path, 'wb') as f:
                pickle.dump(encoder, f)
        
        # Save metadata
        metadata = {
            'algorithm': model_result['algorithm'],
            'training_time': model_result['training_time'],
            'parameters': model_result.get('parameters', {}),
            'feature_importance': model_result.get('feature_importance', {}),
            'saved_at': datetime.now().isoformat()
        }
        
        metadata_path = save_path.replace('.pkl', '_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return {
            'model_path': save_path,
            'scaler_path': scaler_path,
            'encoder_path': encoder_path,
            'metadata_path': metadata_path
        }

class RiskAssessmentTrainer(ModelTrainer):
    """Specialized trainer for risk assessment models."""
    
    def prepare_risk_data(self, df, target_column='recidivism_risk'):
        """Prepare data for risk assessment model."""
        # Separate features and target
        X = df.drop(columns=[target_column])
        y = df[target_column]
        
        # Handle categorical variables
        categorical_cols = X.select_dtypes(include=['object']).columns
        numerical_cols = X.select_dtypes(include=[np.number]).columns
        
        # One-hot encode categorical variables
        if len(categorical_cols) > 0:
            encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
            X_encoded = encoder.fit_transform(X[categorical_cols])
            encoded_feature_names = encoder.get_feature_names_out(categorical_cols)
            
            # Create DataFrame for encoded features
            X_encoded_df = pd.DataFrame(X_encoded, columns=encoded_feature_names)
            
            # Combine with numerical features
            X_final = pd.concat([X[numerical_cols].reset_index(drop=True), 
                                X_encoded_df.reset_index(drop=True)], axis=1)
        else:
            X_final = X.copy()
            encoder = None
        
        # Scale numerical features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_final)
        X_final = pd.DataFrame(X_scaled, columns=X_final.columns)
        
        return X_final, y, scaler, encoder
    
    def train_risk_model(self, dataset_path, algorithm='random_forest', target_column='recidivism_risk'):
        """Train risk assessment model from dataset."""
        # Load dataset
        if dataset_path.endswith('.csv'):
            df = pd.read_csv(dataset_path)
        elif dataset_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(dataset_path)
        else:
            raise ValueError("Unsupported file format")
        
        # Prepare data
        X, y, scaler, encoder = self.prepare_risk_data(df, target_column)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Train model
        model_result = self.train_model(algorithm, X_train, y_train)
        
        # Evaluate model
        metrics = self.evaluate_model(model_result['model'], X_test, y_test)
        
        return {
            'model_result': model_result,
            'metrics': metrics,
            'scaler': scaler,
            'encoder': encoder,
            'feature_names': X.columns.tolist(),
            'data_shape': {
                'train': (len(X_train), len(X_train.columns)),
                'test': (len(X_test), len(X_test.columns))
            }
        }

class ProgramRecommenderTrainer(ModelTrainer):
    """Specialized trainer for program recommendation models."""
    
    def prepare_recommendation_data(self, df, user_id_col='offender_id', 
                                   program_col='program_id', rating_col='rating'):
        """Prepare data for recommendation system."""
        # This is a simplified collaborative filtering approach
        from sklearn.preprocessing import LabelEncoder
        
        # Encode user and program IDs
        user_encoder = LabelEncoder()
        program_encoder = LabelEncoder()
        
        df['user_encoded'] = user_encoder.fit_transform(df[user_id_col])
        df['program_encoded'] = program_encoder.fit_transform(df[program_col])
        
        # Create user-program matrix
        n_users = len(user_encoder.classes_)
        n_programs = len(program_encoder.classes_)
        
        # For simplicity, we'll use a matrix factorization approach
        # In practice, you might use Surprise or LightFM library
        
        return {
            'user_encoder': user_encoder,
            'program_encoder': program_encoder,
            'n_users': n_users,
            'n_programs': n_programs,
            'ratings': df[[rating_col, 'user_encoded', 'program_encoded']].values
        }
    
    def train_recommender(self, dataset_path, algorithm='matrix_factorization'):
        """Train program recommendation model."""
        # Load dataset
        if dataset_path.endswith('.csv'):
            df = pd.read_csv(dataset_path)
        elif dataset_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(dataset_path)
        else:
            raise ValueError("Unsupported file format")
        
        # Prepare data
        prepared_data = self.prepare_recommendation_data(df)
        
        # For now, return basic statistics
        # In a real implementation, you would train a recommendation model
        
        return {
            'prepared_data': prepared_data,
            'statistics': {
                'n_users': prepared_data['n_users'],
                'n_programs': prepared_data['n_programs'],
                'n_ratings': len(df)
            }
        }
