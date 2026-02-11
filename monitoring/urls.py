"""
URLs for monitoring app.
"""
from django.urls import path
from . import views

app_name = 'monitoring'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.monitoring_dashboard, name='dashboard'),
    path('statistics/', views.monitoring_statistics, name='statistics'),
    
    # Check-in Types
    path('checkin-types/', views.CheckInTypeListView.as_view(), name='checkintype_list'),
    path('checkin-types/create/', views.CheckInTypeCreateView.as_view(), name='checkintype_create'),
    path('checkin-types/<int:pk>/update/', views.CheckInTypeUpdateView.as_view(), name='checkintype_update'),
    path('checkin-types/<int:pk>/delete/', views.CheckInTypeDeleteView.as_view(), name='checkintype_delete'),
    
    # Check-ins
    path('checkins/', views.CheckInListView.as_view(), name='checkin_list'),
    path('checkins/create/', views.CheckInCreateView.as_view(), name='checkin_create'),
    path('checkins/quick/', views.quick_checkin, name='quick_checkin'),
    path('checkins/<int:pk>/', views.CheckInDetailView.as_view(), name='checkin_detail'),
    path('checkins/<int:pk>/update/', views.CheckInUpdateView.as_view(), name='checkin_update'),
    path('checkins/<int:pk>/delete/', views.CheckInDeleteView.as_view(), name='checkin_delete'),
    path('checkins/<int:checkin_id>/complete/', views.mark_checkin_completed, name='mark_checkin_completed'),
    
    # GPS Monitoring
    path('gps/', views.GPSMonitoringListView.as_view(), name='gps_list'),
    path('gps/create/', views.GPSMonitoringCreateView.as_view(), name='gps_create'),
    path('gps/<int:pk>/', views.GPSMonitoringDetailView.as_view(), name='gps_detail'),
    path('gps/<int:pk>/update/', views.GPSMonitoringUpdateView.as_view(), name='gps_update'),
    path('gps/<int:pk>/delete/', views.GPSMonitoringDeleteView.as_view(), name='gps_delete'),
    
    # Drug Tests
    path('drug-tests/', views.DrugTestListView.as_view(), name='drugtest_list'),
    path('drug-tests/create/', views.DrugTestCreateView.as_view(), name='drugtest_create'),
    path('drug-tests/<int:pk>/', views.DrugTestDetailView.as_view(), name='drugtest_detail'),
    path('drug-tests/<int:pk>/update/', views.DrugTestUpdateView.as_view(), name='drugtest_update'),
    
    # Employment Verification
    path('employment/', views.EmploymentVerificationListView.as_view(), name='employment_list'),
    path('employment/create/', views.EmploymentVerificationCreateView.as_view(), name='employment_create'),
    path('employment/<int:pk>/', views.EmploymentVerificationDetailView.as_view(), name='employment_detail'),
    path('employment/<int:pk>/update/', views.EmploymentVerificationUpdateView.as_view(), name='employment_update'),
    
    # Alerts
    path('alerts/', views.AlertListView.as_view(), name='alert_list'),
    path('alerts/create/', views.create_alert, name='alert_create'),
    path('alerts/<int:pk>/', views.AlertDetailView.as_view(), name='alert_detail'),
    path('alerts/<int:pk>/update/', views.AlertUpdateView.as_view(), name='alert_update'),
    path('alerts/<int:alert_id>/acknowledge/', views.acknowledge_alert, name='acknowledge_alert'),
    path('alerts/<int:alert_id>/resolve/', views.resolve_alert, name='resolve_alert'),
    
    # Reports
    path('compliance-report/', views.compliance_report, name='compliance_report'),
    path('export-compliance-report/', views.export_compliance_report, name='export_compliance_report'),
    
    # Offender Monitoring
    path('offender/<int:offender_id>/summary/', views.offender_monitoring_summary, name='offender_summary'),
]