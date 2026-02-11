"""
Admin configuration for accounts app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    """Custom User Admin interface."""
    
    model = User
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'date_created']
    list_filter = ['role', 'is_active', 'is_staff', 'date_created']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'phone', 'profile_picture')}),
        ('Role & Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined', 'date_created', 'date_updated')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'is_staff', 'is_active'),
        }),
    )
    
    readonly_fields = ['date_created', 'date_updated']

admin.site.register(User, CustomUserAdmin)