"""
URLs for datasets app.
"""
from django.urls import path
from . import views

app_name = 'datasets'

urlpatterns = [
    # Dataset URLs
    path('', views.DatasetListView.as_view(), name='dataset_list'),
    path('upload/', views.DatasetUploadView.as_view(), name='dataset_upload'),
    path('<int:pk>/', views.DatasetDetailView.as_view(), name='dataset_detail'),
    path('<int:pk>/update/', views.DatasetUpdateView.as_view(), name='dataset_update'),
    path('<int:pk>/delete/', views.DatasetDeleteView.as_view(), name='dataset_delete'),
    path('<int:pk>/analyze/', views.analyze_dataset, name='dataset_analyze'),
    path('<int:pk>/preview/', views.preview_dataset, name='dataset_preview'),
    path('<int:pk>/clean/', views.clean_dataset, name='dataset_clean'),
    path('<int:pk>/download/', views.download_dataset, name='dataset_download'),
    path('<int:pk>/bulk-feature-mapping/', views.bulk_feature_mapping, name='bulk_feature_mapping'),
    
    # Dataset Source URLs
    path('sources/', views.DatasetSourceListView.as_view(), name='source_list'),
    path('sources/create/', views.DatasetSourceCreateView.as_view(), name='source_create'),
    
    # Feature Map URLs
    path('<int:dataset_id>/featuremaps/create/', 
         views.FeatureMapCreateView.as_view(), name='featuremap_create'),
    path('featuremaps/<int:pk>/update/', 
         views.FeatureMapUpdateView.as_view(), name='featuremap_update'),
    path('featuremaps/<int:pk>/delete/', 
         views.FeatureMapDeleteView.as_view(), name='featuremap_delete'),
    
    # Statistics
    path('statistics/', views.dataset_statistics, name='dataset_statistics'),
]