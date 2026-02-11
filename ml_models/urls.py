"""
URLs for ml_models app.
"""
from django.urls import path
from . import views

app_name = 'ml_models'

urlpatterns = [
    # ML Model URLs
    path('', views.MLModelListView.as_view(), name='model_list'),
    path('create/', views.MLModelCreateView.as_view(), name='model_create'),
    path('<int:pk>/', views.MLModelDetailView.as_view(), name='model_detail'),
    path('<int:pk>/update/', views.MLModelUpdateView.as_view(), name='model_update'),
    path('<int:pk>/delete/', views.MLModelDeleteView.as_view(), name='model_delete'),
    path('<int:pk>/deploy/', views.deploy_model, name='model_deploy'),
    path('<int:pk>/retire/', views.retire_model, name='model_retire'),
    path('<int:pk>/performance/', views.model_performance, name='model_performance'),
    
    # Training Job URLs
    path('jobs/', views.TrainingJobListView.as_view(), name='trainingjob_list'),
    path('jobs/<int:pk>/', views.TrainingJobDetailView.as_view(), name='trainingjob_detail'),
    
    # Prediction URLs
    path('predictions/', views.PredictionListView.as_view(), name='prediction_list'),
    path('predictions/<int:pk>/', views.PredictionDetailView.as_view(), name='prediction_detail'),
    
    # ML Operations URLs
    path('train/', views.train_model, name='train_model'),
    path('predict/', views.make_prediction, name='make_prediction'),
    path('batch-predict/', views.batch_prediction, name='batch_prediction'),
    path('get-model-features/', views.get_model_features, name='get_model_features'),
    
    # Dashboard
    path('dashboard/', views.ml_dashboard, name='ml_dashboard'),
]