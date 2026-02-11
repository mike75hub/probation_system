"""
URLs for programs app.
"""
from django.urls import path
from . import views

app_name = 'programs'

urlpatterns = [
    # Program Categories
    path('categories/', views.ProgramCategoryListView.as_view(), name='category_list'),
    path('categories/create/', views.ProgramCategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/update/', views.ProgramCategoryUpdateView.as_view(), name='category_update'),
    path('categories/<int:pk>/delete/', views.ProgramCategoryDeleteView.as_view(), name='category_delete'),
    
    # Programs
    path('', views.ProgramListView.as_view(), name='program_list'),
    path('create/', views.ProgramCreateView.as_view(), name='program_create'),
    path('<int:pk>/', views.ProgramDetailView.as_view(), name='program_detail'),
    path('<int:pk>/update/', views.ProgramUpdateView.as_view(), name='program_update'),
    path('<int:pk>/delete/', views.ProgramDeleteView.as_view(), name='program_delete'),
    
    # Enrollments
    path('enrollments/', views.EnrollmentListView.as_view(), name='enrollment_list'),
    path('enrollments/create/', views.EnrollmentCreateView.as_view(), name='enrollment_create'),
    path('enrollments/<int:pk>/', views.EnrollmentDetailView.as_view(), name='enrollment_detail'),
    path('enrollments/<int:pk>/update/', views.EnrollmentUpdateView.as_view(), name='enrollment_update'),
    path('enrollments/<int:pk>/delete/', views.EnrollmentDeleteView.as_view(), name='enrollment_delete'),
    
    # Sessions
    path('sessions/create/', views.SessionCreateView.as_view(), name='session_create'),
    path('sessions/<int:pk>/update/', views.SessionUpdateView.as_view(), name='session_update'),
    
    # Attendance
    path('sessions/<int:session_id>/attendance/', views.session_attendance, name='session_attendance'),
    path('sessions/<int:session_id>/take-attendance/', views.take_attendance, name='take_attendance'),
    
    # Operations
    path('dashboard/', views.program_dashboard, name='program_dashboard'),
    path('statistics/', views.program_statistics, name='program_statistics'),
    path('enrollments/<int:enrollment_id>/generate-certificate/', views.generate_certificate, name='generate_certificate'),
    path('offenders/<int:offender_id>/recommend-programs/', views.recommend_programs, name='recommend_programs'),
]