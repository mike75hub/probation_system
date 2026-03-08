"""
Views for ml_models app.
"""
import json
import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Avg, Q
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
import os
from datetime import datetime, timedelta

from .models import MLModel, TrainingJob, Prediction
from .forms import (
    MLModelForm, TrainingJobForm, PredictionForm, 
    ModelTrainingForm, SinglePredictionForm, BatchPredictionForm
)
from .trainers import ModelTrainer, RiskAssessmentTrainer
from .predictors import PredictionService
from .ml_pipeline import MLPipeline
from datasets.models import Dataset

# ML Model Views
class MLModelListView(LoginRequiredMixin, ListView):
    model = MLModel
    template_name = 'ml_models/model_list.html'
    context_object_name = 'models'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by type if provided
        model_type = self.request.GET.get('type')
        if model_type:
            queryset = queryset.filter(model_type=model_type)
        
        # Filter by algorithm if provided
        algorithm = self.request.GET.get('algorithm')
        if algorithm:
            queryset = queryset.filter(algorithm=algorithm)
        
        # Filter by status if provided
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Show only active models by default
        show_inactive = self.request.GET.get('show_inactive')
        if not show_inactive:
            queryset = queryset.filter(is_active=True)
        
        # Search if provided
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(purpose__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add statistics
        context['total_models'] = MLModel.objects.count()
        context['active_models'] = MLModel.objects.filter(is_active=True).count()
        context['deployed_models'] = MLModel.objects.filter(status='deployed').count()
        
        # Performance summary
        context['avg_accuracy'] = MLModel.objects.filter(
            accuracy__isnull=False
        ).aggregate(avg=Avg('accuracy'))['avg'] or 0
        
        # Models by type
        context['models_by_type'] = MLModel.objects.values('model_type').annotate(
            count=Count('id')
        )
        
        # Recent training jobs
        context['recent_jobs'] = TrainingJob.objects.order_by('-created_at')[:5]
        
        return context

class MLModelDetailView(LoginRequiredMixin, DetailView):
    model = MLModel
    template_name = 'ml_models/model_detail.html'
    context_object_name = 'model'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        model = self.object
        
        # Add related data
        context['training_jobs'] = TrainingJob.objects.filter(ml_model=model).order_by('-created_at')[:10]
        context['recent_predictions'] = Prediction.objects.filter(ml_model=model).order_by('-prediction_time')[:10]
        
        # Performance history
        context['prediction_count'] = Prediction.objects.filter(ml_model=model).count()
        
        # Accuracy over time (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_predictions = Prediction.objects.filter(
            ml_model=model,
            prediction_time__gte=thirty_days_ago,
            is_correct__isnull=False
        )
        
        if recent_predictions.exists():
            correct = recent_predictions.filter(is_correct=True).count()
            total = recent_predictions.count()
            context['recent_accuracy'] = (correct / total * 100) if total > 0 else 0
        else:
            context['recent_accuracy'] = None
        
        # Add prediction form
        context['prediction_form'] = SinglePredictionForm(initial={'ml_model': model})
        
        return context

class MLModelCreateView(LoginRequiredMixin, CreateView):
    model = MLModel
    form_class = MLModelForm
    template_name = 'ml_models/model_form.html'
    success_url = reverse_lazy('ml_models:model_list')
    
    def form_valid(self, form):
        form.instance.trained_by = self.request.user
        form.instance.status = 'trained'  # Default status
        
        messages.success(self.request, f"ML Model '{form.instance.name}' created successfully!")
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

class MLModelUpdateView(LoginRequiredMixin, UpdateView):
    model = MLModel
    form_class = MLModelForm
    template_name = 'ml_models/model_form.html'
    
    def get_success_url(self):
        return reverse_lazy('ml_models:model_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f"ML Model '{self.object.name}' updated successfully!")
        return super().form_valid(form)

class MLModelDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = MLModel
    template_name = 'ml_models/model_delete.html'
    success_url = reverse_lazy('ml_models:model_list')
    permission_required = 'ml_models.delete_mlmodel'
    
    def delete(self, request, *args, **kwargs):
        model = self.get_object()
        messages.success(request, f"ML Model '{model.name}' deleted successfully!")
        return super().delete(request, *args, **kwargs)

# Training Job Views
class TrainingJobListView(LoginRequiredMixin, ListView):
    model = TrainingJob
    template_name = 'ml_models/trainingjob_list.html'
    context_object_name = 'jobs'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status if provided
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Search if provided
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(job_id__icontains=search) |
                Q(ml_model__name__icontains=search) |
                Q(error_message__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add statistics
        context['total_jobs'] = TrainingJob.objects.count()
        context['completed_jobs'] = TrainingJob.objects.filter(status='completed').count()
        context['failed_jobs'] = TrainingJob.objects.filter(status='failed').count()
        context['running_jobs'] = TrainingJob.objects.filter(status='running').count()
        
        # Jobs by status
        context['jobs_by_status'] = TrainingJob.objects.values('status').annotate(
            count=Count('id')
        )
        
        return context

class TrainingJobDetailView(LoginRequiredMixin, DetailView):
    model = TrainingJob
    template_name = 'ml_models/trainingjob_detail.html'
    context_object_name = 'job'

# Prediction Views
class PredictionListView(LoginRequiredMixin, ListView):
    model = Prediction
    template_name = 'ml_models/prediction_list.html'
    context_object_name = 'predictions'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by model if provided
        model_id = self.request.GET.get('model')
        if model_id:
            queryset = queryset.filter(ml_model_id=model_id)
        
        # Filter by correctness if provided
        is_correct = self.request.GET.get('is_correct')
        if is_correct is not None:
            queryset = queryset.filter(is_correct=is_correct)
        
        # Filter by date range if provided
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            queryset = queryset.filter(prediction_time__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(prediction_time__date__lte=date_to)
        
        # Search if provided
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(offender__user__first_name__icontains=search) |
                Q(offender__user__last_name__icontains=search) |
                Q(predicted_class__icontains=search) |
                Q(ml_model__name__icontains=search)
            )
        
        return queryset.order_by('-prediction_time')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add statistics
        context['total_predictions'] = Prediction.objects.count()
        context['correct_predictions'] = Prediction.objects.filter(is_correct=True).count()
        context['incorrect_predictions'] = Prediction.objects.filter(is_correct=False).count()
        
        # Accuracy
        total_with_truth = Prediction.objects.filter(is_correct__isnull=False).count()
        if total_with_truth > 0:
            correct = Prediction.objects.filter(is_correct=True).count()
            context['accuracy'] = (correct / total_with_truth) * 100
        else:
            context['accuracy'] = None
        
        # Predictions by model
        context['predictions_by_model'] = Prediction.objects.values(
            'ml_model__name'
        ).annotate(
            count=Count('id'),
            avg_confidence=Avg('prediction_confidence')
        )
        
        # Recent models for filter
        context['recent_models'] = MLModel.objects.filter(is_active=True).order_by('-created_at')[:10]
        
        return context

class PredictionDetailView(LoginRequiredMixin, DetailView):
    model = Prediction
    template_name = 'ml_models/prediction_detail.html'
    context_object_name = 'prediction'

# Function-based views for ML operations
@login_required
def train_model(request):
    """Train a new ML model."""
    if request.method == 'POST':
        form = ModelTrainingForm(request.POST, user=request.user)
        
        if form.is_valid():
            try:
                # Get form data
                name = form.cleaned_data['name']
                description = form.cleaned_data['description']
                dataset = form.cleaned_data['dataset']
                algorithm = form.cleaned_data['algorithm']
                model_type = form.cleaned_data['model_type']
                target_column = form.cleaned_data['target_column']
                
                # Create ML model record
                ml_model = MLModel.objects.create(
                    name=name,
                    description=description,
                    model_type=model_type,
                    algorithm=algorithm,
                    purpose=f"Predict {target_column}",
                    trained_by=request.user,
                    training_dataset=dataset,
                    status='training',
                    target_column=target_column
                )
                
                # Create training job
                job = TrainingJob.objects.create(
                    ml_model=ml_model,
                    dataset=dataset,
                    job_id=f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    status='running',
                    parameters={
                        'algorithm': algorithm,
                        'model_type': model_type,
                        'target_column': target_column,
                        'test_size': form.cleaned_data['test_size'],
                        'random_state': form.cleaned_data['random_state']
                    }
                )
                
                # Run training in background (simplified)
                # In production, use Celery or similar
                try:
                    pipeline = MLPipeline()
                    
                    if 'risk' in name.lower():
                        result = pipeline.run_risk_assessment_pipeline(
                            dataset.original_file.path,
                            model_name=name
                        )
                    else:
                        # Generic training
                        trainer = ModelTrainer()
                        
                        # Load and prepare data
                        import pandas as pd
                        if dataset.original_file.path.endswith('.csv'):
                            df = pd.read_csv(dataset.original_file.path)
                        else:
                            df = pd.read_excel(dataset.original_file.path)

                        if target_column not in df.columns:
                            raise ValueError(f"Target column '{target_column}' was not found in the dataset.")

                        # Split features and target
                        X = df.drop(columns=[target_column]).copy()
                        y = df[target_column].copy()

                        # Clean infinities and all-null columns
                        X = X.replace([float('inf'), float('-inf')], pd.NA)
                        X = X.dropna(axis=1, how='all')
                        if X.empty:
                            raise ValueError("No usable feature columns found after preprocessing.")

                        # Fill missing values in features
                        numeric_cols = X.select_dtypes(include=['number']).columns
                        categorical_cols = X.select_dtypes(exclude=['number']).columns

                        if len(numeric_cols) > 0:
                            X[numeric_cols] = X[numeric_cols].apply(lambda col: col.fillna(col.median()))
                        if len(categorical_cols) > 0:
                            X[categorical_cols] = X[categorical_cols].astype(str).fillna('missing')

                        # One-hot encode categorical feature columns
                        X = pd.get_dummies(X, columns=list(categorical_cols), drop_first=False, dtype=float)

                        # Prepare target by selected model type
                        if model_type == 'regression':
                            y = pd.to_numeric(y, errors='coerce')
                            valid_rows = y.notna()
                            X = X.loc[valid_rows]
                            y = y.loc[valid_rows]
                            if y.empty:
                                raise ValueError("Target column has no numeric values for regression.")
                        else:
                            y = y.astype(str).fillna('missing')
                            valid_rows = y.notna()
                            X = X.loc[valid_rows]
                            y = y.loc[valid_rows]
                            if y.nunique() < 2:
                                raise ValueError("Classification target must have at least 2 classes.")

                        if X.empty:
                            raise ValueError("No rows available for training after preprocessing.")

                        # Persist the transformed feature list used by the model
                        ml_model.feature_columns = X.columns.tolist()
                        ml_model.save(update_fields=['feature_columns'])

                        # Train model using selected model type
                        model_result = trainer.train_model(
                            algorithm,
                            X,
                            y,
                            model_type=model_type
                        )
                        
                        # Save model
                        model_dir = os.path.join('media/ml_models', datetime.now().strftime('%Y/%m/%d'))
                        os.makedirs(model_dir, exist_ok=True)
                        
                        model_filename = f"{name.replace(' ', '_').lower()}.pkl"
                        model_path = os.path.join(model_dir, model_filename)
                        
                        trainer.save_model(model_result, model_path)
                        
                        # Update ML model
                        ml_model.model_file.name = model_path
                        ml_model.status = 'trained'
                        ml_model.training_time_seconds = model_result['training_time']
                        ml_model.save()
                        
                        result = {'success': True}
                    
                    if result.get('success'):
                        job.status = 'completed'
                        job.metrics = result.get('metrics', {})
                        job.completed_at = datetime.now()
                        
                        if 'model_id' in result:
                            ml_model.id = result['model_id']
                    else:
                        job.status = 'failed'
                        job.error_message = result.get('error', 'Training failed')
                        ml_model.status = 'error'
                    
                    job.save()
                    ml_model.save()
                    
                    if job.status == 'completed':
                        messages.success(request, f"Model '{name}' trained successfully!")
                    else:
                        messages.error(request, f"Model training failed: {job.error_message}")
                    
                except Exception as e:
                    job.status = 'failed'
                    job.error_message = str(e)
                    job.completed_at = datetime.now()
                    job.save()
                    
                    ml_model.status = 'error'
                    ml_model.save()
                    
                    messages.error(request, f"Error during training: {str(e)}")
                
                return redirect('ml_models:model_detail', pk=ml_model.pk)
                
            except Exception as e:
                messages.error(request, f"Error creating training job: {str(e)}")
                return render(request, 'ml_models/train_model.html', {'form': form})
    
    else:
        form = ModelTrainingForm(user=request.user)
    
    return render(request, 'ml_models/train_model.html', {'form': form})

@login_required
def make_prediction(request):
    """Make a single prediction."""
    if request.method == 'POST':
        form = SinglePredictionForm(request.POST)
        
        if form.is_valid():
            try:
                ml_model = form.cleaned_data['ml_model']
                
                # Extract features from form
                features = {}
                feature_columns = ml_model.feature_columns or []
                
                for feature in feature_columns:
                    field_name = f'feature_{feature}'
                    if field_name in form.cleaned_data:
                        features[feature] = form.cleaned_data[field_name]
                
                # For demo, use a mock offender
                from offenders.models import Offender
                offender = Offender.objects.first()  # In real app, select appropriate offender
                
                # Make prediction
                result = PredictionService.make_prediction(ml_model, offender, features)
                
                if result['success']:
                    messages.success(request, "Prediction made successfully!")
                    return redirect('ml_models:prediction_detail', pk=result['prediction'].pk)
                else:
                    messages.error(request, f"Prediction failed: {result['error']}")
                
            except Exception as e:
                messages.error(request, f"Error making prediction: {str(e)}")
    
    else:
        form = SinglePredictionForm()
    
    return render(request, 'ml_models/make_prediction.html', {'form': form})

@login_required
def batch_prediction(request):
    """Make batch predictions from file."""
    if request.method == 'POST':
        form = BatchPredictionForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                ml_model = form.cleaned_data['ml_model']
                input_file = form.cleaned_data['input_file']
                
                # Read CSV file
                df = pd.read_csv(input_file)
                
                # Make predictions for each row
                predictions = []
                predictor = PredictionService.get_predictor_for_model(ml_model)
                
                for index, row in df.iterrows():
                    features = row.to_dict()
                    
                    # For demo, use a mock offender
                    from offenders.models import Offender
                    offender = Offender.objects.first()
                    
                    # Make prediction
                    prediction, _ = predictor.predict(features)
                    
                    # Save prediction
                    pred = Prediction.objects.create(
                        ml_model=ml_model,
                        offender=offender,
                        input_features=features,
                        predicted_value=float(prediction[0]) if hasattr(prediction, '__len__') else prediction,
                        predicted_class=str(prediction),
                        made_by=request.user,
                        batch_id=f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    )
                    
                    predictions.append(pred)
                
                messages.success(request, f"Made {len(predictions)} predictions successfully!")
                
                # Create summary report
                report = {
                    'total_predictions': len(predictions),
                    'model_used': ml_model.name,
                    'timestamp': datetime.now().isoformat()
                }
                
                return render(request, 'ml_models/batch_prediction_results.html', {
                    'predictions': predictions,
                    'report': report
                })
                
            except Exception as e:
                messages.error(request, f"Error making batch predictions: {str(e)}")
    
    else:
        form = BatchPredictionForm()
    
    return render(request, 'ml_models/batch_prediction.html', {'form': form})

@login_required
@csrf_exempt
def get_model_features(request):
    """Get feature columns for a model (AJAX)."""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            model_id = request.POST.get('model_id')
            model = get_object_or_404(MLModel, pk=model_id)
            
            feature_columns = model.feature_columns or []
            
            return JsonResponse({
                'success': True,
                'features': feature_columns
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def deploy_model(request, pk):
    """Deploy a trained model."""
    model = get_object_or_404(MLModel, pk=pk)
    
    if model.status not in ['trained', 'validating']:
        messages.error(request, f"Cannot deploy model with status: {model.get_status_display()}")
        return redirect('ml_models:model_detail', pk=pk)
    
    model.status = 'deployed'
    model.deployed_at = datetime.now()
    model.save()
    
    messages.success(request, f"Model '{model.name}' deployed successfully!")
    return redirect('ml_models:model_detail', pk=pk)

@login_required
def retire_model(request, pk):
    """Retire a deployed model."""
    model = get_object_or_404(MLModel, pk=pk)
    
    model.status = 'retired'
    model.is_active = False
    model.save()
    
    messages.success(request, f"Model '{model.name}' retired successfully!")
    return redirect('ml_models:model_detail', pk=pk)

@login_required
def model_performance(request, pk):
    """View model performance metrics."""
    model = get_object_or_404(MLModel, pk=pk)
    
    # Get predictions with ground truth
    predictions = Prediction.objects.filter(
        ml_model=model,
        actual_value__isnull=False
    ).order_by('-prediction_time')
    
    # Calculate metrics
    if model.model_type == 'classification':
        correct = predictions.filter(is_correct=True).count()
        total = predictions.count()
        accuracy = (correct / total * 100) if total > 0 else 0
        
        performance_metrics = {
            'accuracy': accuracy,
            'correct_predictions': correct,
            'total_predictions': total,
        }
    elif model.model_type == 'regression':
        errors = []
        for pred in predictions:
            if pred.actual_value is not None and pred.predicted_value is not None:
                errors.append(abs(pred.actual_value - pred.predicted_value))
        
        if errors:
            performance_metrics = {
                'mae': sum(errors) / len(errors),
                'max_error': max(errors),
                'min_error': min(errors),
                'total_predictions': len(errors),
            }
        else:
            performance_metrics = {'error': 'No ground truth data available'}
    else:
        performance_metrics = {'error': 'Unsupported model type'}
    
    context = {
        'model': model,
        'predictions': predictions[:50],  # Show recent predictions
        'performance_metrics': performance_metrics,
        'prediction_count': predictions.count(),
    }
    
    return render(request, 'ml_models/model_performance.html', context)

@login_required
def ml_dashboard(request):
    """ML Dashboard view."""
    # Model statistics
    total_models = MLModel.objects.count()
    active_models = MLModel.objects.filter(is_active=True).count()
    deployed_models = MLModel.objects.filter(status='deployed').count()
    
    # Training job statistics
    total_jobs = TrainingJob.objects.count()
    completed_jobs = TrainingJob.objects.filter(status='completed').count()
    failed_jobs = TrainingJob.objects.filter(status='failed').count()
    
    # Prediction statistics
    total_predictions = Prediction.objects.count()
    recent_predictions = Prediction.objects.filter(
        prediction_time__gte=datetime.now() - timedelta(days=7)
    ).count()
    
    # Recent activity
    recent_models = MLModel.objects.order_by('-created_at')[:5]
    recent_jobs = TrainingJob.objects.order_by('-created_at')[:5]
    recent_predictions_list = Prediction.objects.order_by('-prediction_time')[:10]
    
    # Performance summary
    avg_accuracy = MLModel.objects.filter(
        accuracy__isnull=False
    ).aggregate(avg=Avg('accuracy'))['avg'] or 0
    
    context = {
        'total_models': total_models,
        'active_models': active_models,
        'deployed_models': deployed_models,
        'total_jobs': total_jobs,
        'completed_jobs': completed_jobs,
        'failed_jobs': failed_jobs,
        'total_predictions': total_predictions,
        'recent_predictions': recent_predictions,
        'recent_models': recent_models,
        'recent_jobs': recent_jobs,
        'recent_predictions_list': recent_predictions_list,
        'avg_accuracy': avg_accuracy,
    }
    
    return render(request, 'ml_models/dashboard.html', context)
