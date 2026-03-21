"""
Custom User model for the probation system.
"""
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    """Custom User model with role-based authentication."""
    
    class Role(models.TextChoices):
        ADMIN = 'admin', _('System Administrator')
        OFFICER = 'officer', _('Probation Officer')
        OFFENDER = 'offender', _('Offender')
        JUDICIARY = 'judiciary', _('Judiciary Staff')
        NGO = 'ngo', _('NGO Staff')
    
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.OFFICER,
        verbose_name=_('User Role')
    )
    phone = models.CharField(
        max_length=15,
        blank=True,
        verbose_name=_('Phone Number')
    )
    designation = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Designation')
    )
    profile_picture = models.ImageField(
        upload_to='profiles/',
        blank=True,
        null=True,
        verbose_name=_('Profile Picture')
    )
    date_created = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Date Created')
    )
    date_updated = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Date Updated')
    )
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-date_created']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"
    
    def is_admin(self):
        return self.role == self.Role.ADMIN
    
    def is_officer(self):
        return self.role == self.Role.OFFICER
    
    def is_offender(self):
        return self.role == self.Role.OFFENDER
    
    def get_role_display_name(self):
        return self.get_role_display()
