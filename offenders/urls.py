"""
URLs for offenders app.
"""
from django.urls import path
from . import views

app_name = 'offenders'

urlpatterns = [
    path('', views.offender_list, name='offender_list'),
    path('stats/', views.dashboard_stats, name='offender_stats'),
    path('assessments/', views.assessment_list, name='assessment_list'),

    
    # Offender CRUD
    path('create/', views.offender_create, name='offender_create'),
    path('<int:pk>/', views.offender_detail, name='offender_detail'),
    path('<int:pk>/edit/', views.offender_update, name='offender_update'),
    path('<int:pk>/delete/', views.offender_delete, name='offender_delete'),
    
    # Cases
    path('<int:offender_pk>/cases/create/', views.case_create, name='case_create'),
    
    # Assessments
    path('<int:offender_pk>/assessments/create/', views.assessment_create, name='assessment_create'),
]