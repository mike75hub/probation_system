"""
Views for datasets app.
"""
import os
import json
import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Sum, Avg
from .models import Dataset, DatasetSource, FeatureMap
from .forms import DatasetUploadForm, DatasetSourceForm, FeatureMapForm, DatasetAnalysisForm, DatasetPreviewForm, DatasetUpdateForm
from .processors import DatasetProcessor

# Dataset Views
class DatasetListView(LoginRequiredMixin, ListView):
    model = Dataset
    template_name = 'datasets/dataset_list.html'
    context_object_name = 'datasets'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by type if provided
        dataset_type = self.request.GET.get('type')
        if dataset_type:
            queryset = queryset.filter(dataset_type=dataset_type)
        
        # Filter by status if provided
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Search if provided
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        return queryset.order_by('-upload_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add statistics
        context['total_datasets'] = Dataset.objects.count()
        total_bytes = Dataset.objects.aggregate(total=Sum('file_size'))['total'] or 0
        context['total_size_gb'] = round(total_bytes / (1024**3), 2)
        context['datasets_by_type'] = Dataset.objects.values('dataset_type').annotate(count=Count('id'))
        context['datasets_by_status'] = Dataset.objects.values('status').annotate(count=Count('id'))
        
        return context

class DatasetDetailView(LoginRequiredMixin, DetailView):
    model = Dataset
    template_name = 'datasets/dataset_detail.html'
    context_object_name = 'dataset'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dataset = self.object
        
        # Add feature maps
        context['feature_maps'] = FeatureMap.objects.filter(dataset=dataset)
        
        # Add preview form
        context['preview_form'] = DatasetPreviewForm()
        
        # Add analysis form
        context['analysis_form'] = DatasetAnalysisForm()
        
        # Get sample data
        try:
            preview_data = dataset.get_preview_data(rows=5)
            context['preview_data'] = preview_data
            context['preview_columns'] = dataset.column_names if dataset.column_names else []
        except Exception as e:
            context['preview_error'] = str(e)
        
        return context

class DatasetUploadView(LoginRequiredMixin, CreateView):
    model = Dataset
    form_class = DatasetUploadForm
    template_name = 'datasets/dataset_upload.html'
    success_url = reverse_lazy('datasets:dataset_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Dataset '{self.object.name}' uploaded successfully!")
        
        # Analyze the dataset
        try:
            if self.object.analyze_data():
                messages.info(self.request, "Dataset analyzed successfully.")
        except Exception as e:
            messages.warning(self.request, f"Dataset uploaded but analysis failed: {str(e)}")
        
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

class DatasetUpdateView(LoginRequiredMixin, UpdateView):
    model = Dataset
    form_class = DatasetUpdateForm
    template_name = 'datasets/dataset_update.html'
    
    def get_success_url(self):
        return reverse_lazy('datasets:dataset_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f"Dataset '{self.object.name}' updated successfully!")
        return super().form_valid(form)

class DatasetDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Dataset
    template_name = 'datasets/dataset_delete.html'
    success_url = reverse_lazy('datasets:dataset_list')
    permission_required = 'datasets.delete_dataset'
    
    def delete(self, request, *args, **kwargs):
        dataset = self.get_object()
        messages.success(request, f"Dataset '{dataset.name}' deleted successfully!")
        return super().delete(request, *args, **kwargs)

# Dataset Source Views
class DatasetSourceListView(LoginRequiredMixin, ListView):
    model = DatasetSource
    template_name = 'datasets/source_list.html'
    context_object_name = 'sources'
    paginate_by = 20

class DatasetSourceCreateView(LoginRequiredMixin, CreateView):
    model = DatasetSource
    form_class = DatasetSourceForm
    template_name = 'datasets/source_form.html'
    success_url = reverse_lazy('datasets:source_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Data source created successfully!")
        return super().form_valid(form)

# Feature Map Views
class FeatureMapCreateView(LoginRequiredMixin, CreateView):
    model = FeatureMap
    form_class = FeatureMapForm
    template_name = 'datasets/featuremap_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        dataset_id = self.kwargs.get('dataset_id')
        if dataset_id:
            initial['dataset'] = get_object_or_404(Dataset, pk=dataset_id)
        return initial
    
    def form_valid(self, form):
        dataset_id = self.kwargs.get('dataset_id')
        if dataset_id:
            form.instance.dataset = get_object_or_404(Dataset, pk=dataset_id)
        
        response = super().form_valid(form)
        messages.success(self.request, "Feature mapping added successfully!")
        return response
    
    def get_success_url(self):
        return reverse_lazy('datasets:dataset_detail', kwargs={'pk': self.object.dataset.pk})

class FeatureMapUpdateView(LoginRequiredMixin, UpdateView):
    model = FeatureMap
    form_class = FeatureMapForm
    template_name = 'datasets/featuremap_form.html'
    
    def get_success_url(self):
        return reverse_lazy('datasets:dataset_detail', kwargs={'pk': self.object.dataset.pk})
    
    def form_valid(self, form):
        messages.success(self.request, "Feature mapping updated successfully!")
        return super().form_valid(form)

class FeatureMapDeleteView(LoginRequiredMixin, DeleteView):
    model = FeatureMap
    template_name = 'datasets/featuremap_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('datasets:dataset_detail', kwargs={'pk': self.object.dataset.pk})
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Feature mapping deleted successfully!")
        return super().delete(request, *args, **kwargs)

# Function-based views for additional operations
@login_required
def analyze_dataset(request, pk):
    """Analyze dataset and update metrics."""
    dataset = get_object_or_404(Dataset, pk=pk)
    
    if request.method == 'POST':
        form = DatasetAnalysisForm(request.POST)
        if form.is_valid():
            try:
                if dataset.analyze_data():
                    messages.success(request, "Dataset analyzed successfully!")
                else:
                    messages.error(request, "Failed to analyze dataset.")
            except Exception as e:
                messages.error(request, f"Error analyzing dataset: {str(e)}")
    
    return redirect('datasets:dataset_detail', pk=pk)

@login_required
def preview_dataset(request, pk):
    """Preview dataset data."""
    dataset = get_object_or_404(Dataset, pk=pk)
    
    if request.method == 'POST':
        form = DatasetPreviewForm(request.POST)
        if form.is_valid():
            rows = form.cleaned_data['rows_to_preview']
            
            try:
                preview_data = dataset.get_preview_data(rows=rows)
                columns = dataset.column_names
                
                return JsonResponse({
                    'success': True,
                    'data': preview_data,
                    'columns': columns,
                    'row_count': len(preview_data)
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def clean_dataset(request, pk):
    """Clean and preprocess dataset."""
    dataset = get_object_or_404(Dataset, pk=pk)
    
    try:
        processor = DatasetProcessor()
        result = processor.clean_dataset(dataset)
        
        # Update dataset with cleaned file
        dataset.processed_file.name = result['processed_file_path']
        dataset.duplicate_rows = result['duplicates_removed']
        dataset.status = 'ready'
        dataset.save()
        
        messages.success(request, f"Dataset cleaned successfully! Removed {result['duplicates_removed']} duplicates.")
        
    except Exception as e:
        messages.error(request, f"Error cleaning dataset: {str(e)}")
    
    return redirect('datasets:dataset_detail', pk=pk)

@login_required
def download_dataset(request, pk):
    """Download dataset file."""
    dataset = get_object_or_404(Dataset, pk=pk)
    
    if dataset.original_file:
        file_path = dataset.original_file.path
        file_name = os.path.basename(file_path)
        
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{file_name}"'
            return response
    
    messages.error(request, "File not found.")
    return redirect('datasets:dataset_detail', pk=pk)

@login_required
def dataset_statistics(request):
    """Get dataset statistics."""
    total_bytes = Dataset.objects.aggregate(total=Sum('file_size'))['total'] or 0
    stats = {
        'total_datasets': Dataset.objects.count(),
        'total_size_gb': round(total_bytes / (1024**3), 2),
        'avg_quality_score': Dataset.objects.aggregate(avg=Avg('data_quality_score'))['avg'] or 0,
        'datasets_by_type': list(Dataset.objects.values('dataset_type').annotate(count=Count('id'))),
        'datasets_by_status': list(Dataset.objects.values('status').annotate(count=Count('id'))),
        'recent_uploads': list(Dataset.objects.order_by('-upload_date').values('name', 'upload_date')[:10])
    }
    
    return JsonResponse(stats)

@login_required
def bulk_feature_mapping(request, pk):
    """Bulk create feature mappings from dataset columns."""
    dataset = get_object_or_404(Dataset, pk=pk)
    
    if request.method == 'POST':
        try:
            # Get column names from dataset
            columns = dataset.column_names
            
            # Create default feature mappings
            for column in columns:
                # Skip if mapping already exists
                if not FeatureMap.objects.filter(dataset=dataset, source_column=column).exists():
                    FeatureMap.objects.create(
                        dataset=dataset,
                        source_column=column,
                        mapped_feature=column.replace(' ', '_').lower(),
                        feature_type='categorical' if 'id' in column.lower() else 'numerical',
                        is_target=(column.lower() in ['target', 'label', 'class']),
                        is_required=True
                    )
            
            messages.success(request, f"Created feature mappings for {len(columns)} columns.")
            
        except Exception as e:
            messages.error(request, f"Error creating feature mappings: {str(e)}")
    
    return redirect('datasets:dataset_detail', pk=pk)