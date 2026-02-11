"""
URLs for reports app.
"""
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Dashboard
    path('', views.report_dashboard, name='dashboard'),
    
    # Report Generation
    path('generate/', views.generate_report, name='generate'),
    path('quick/<int:report_type_id>/', views.quick_generate_report, name='quick_generate'),
    path('compliance/', views.compliance_report, name='compliance_report'),
    path('performance/', views.performance_report, name='performance_report'),
    
    # Generated Reports Management
    path('reports/', views.ReportListView.as_view(), name='report_list'),
    path('reports/<int:pk>/', views.view_report, name='view_report'),
    path('reports/<int:pk>/download/', views.download_report, name='download_report'),
    path('reports/<int:pk>/delete/', views.ReportDeleteView.as_view(), name='delete_report'),
    
    # Report Scheduling
    path('schedules/', views.ScheduleListView.as_view(), name='schedule_list'),
    path('schedules/new/', views.create_schedule, name='create_schedule'),
    path('schedules/<int:pk>/edit/', views.update_schedule, name='update_schedule'),
    path('schedules/<int:pk>/toggle/', views.toggle_schedule_status, name='toggle_schedule'),
    path('schedules/<int:pk>/delete/', views.delete_schedule, name='delete_schedule'),
    
    # Report Dashboards
    path('dashboards/', views.DashboardListView.as_view(), name='dashboard_list'),
    path('dashboards/new/', views.create_dashboard, name='create_dashboard'),
    path('dashboards/<int:pk>/', views.view_dashboard, name='view_dashboard'),
    path('dashboards/<int:pk>/edit/', views.edit_dashboard, name='edit_dashboard'),
    path('dashboards/<int:pk>/add-report/', views.add_dashboard_report, name='add_dashboard_report'),
    path('dashboards/<int:pk>/report/<int:report_pk>/update/', views.update_dashboard_report, name='update_dashboard_report'),
    path('dashboards/<int:pk>/report/<int:report_pk>/delete/', views.delete_dashboard_report, name='delete_dashboard_report'),
    path('dashboards/<int:pk>/delete/', views.delete_dashboard, name='delete_dashboard'),
    
    # Analytics
    path('analytics/', views.report_analytics, name='analytics'),
    
    # API Endpoints
    path('api/report-data/<int:report_type_id>/', views.api_report_data, name='api_report_data'),
    path('api/dashboard/<int:dashboard_id>/', views.api_dashboard_data, name='api_dashboard_data'),
    
    # Cron Jobs (protected endpoints)
    path('cron/process-scheduled-reports/', views.process_scheduled_reports, name='process_scheduled_reports'),
]