"""
URLs for accounts app.
"""
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts' 

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('register/', views.register_view, name='register'),
    path('settings/', views.settings_view, name='settings'),  # Add this line

    
    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Profile management
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password_view, name='change_password'),
    
    # User management (admin only)
    path('users/', views.users_list_view, name='users_list'),
    path('users/create/', views.create_user_view, name='create_user'),
    path('users/<int:user_id>/', views.user_detail_view, name='user_detail'),
    
    # Password reset (built-in Django views)
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(template_name='accounts/password_reset.html'),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(template_name='accounts/password_reset_confirm.html'),
         name='password_reset_confirm'),
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'),
         name='password_reset_complete'),
]