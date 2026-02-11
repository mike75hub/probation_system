# dashboard/urls.py
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard views
    path('', views.dashboard_view, name='home'),
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('officer/', views.officer_dashboard, name='officer_dashboard'),
    path('offender/', views.offender_dashboard, name='offender_dashboard'),
    path('judiciary/', views.judiciary_dashboard, name='judiciary_dashboard'),
    
    # Dashboard settings
    path('settings/', views.dashboard_settings_view, name='settings'),
    path('reset-layout/', views.reset_dashboard_layout, name='reset_layout'),
    
    # API endpoints
    path('api/stats/', views.dashboard_stats_api, name='stats_api'),
    path('api/charts/<str:chart_type>/', views.dashboard_chart_data, name='chart_data'),
    path('api/notifications/', views.notifications_api, name='notifications_api'),
    path('api/activities/', views.activity_feed_api, name='activity_feed'),
    path('api/health/', views.dashboard_health_check, name='health_check'),
    path('api/export/<str:format>/', views.export_dashboard_data, name='export_data'),
    
    # Widget management
    path('widgets/', views.widget_list, name='widget_list'),
    path('widgets/<int:widget_id>/toggle/', views.toggle_widget, name='toggle_widget'),
]