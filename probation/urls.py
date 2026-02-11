"""
URL configuration for probation project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

app_name = 'probation' 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='dashboard/home.html'), name='home'),
    path('accounts/', include(('accounts.urls', 'accounts'), namespace='accounts')),
    path('offenders/', include(('offenders.urls', 'offenders'), namespace='offenders')),
    path('datasets/', include(('datasets.urls', 'datasets'), namespace='datasets')),
    path('ml-models/', include(('ml_models.urls', 'ml_models'), namespace='ml_models')),
    path('monitoring/', include(('monitoring.urls', 'monitoring'), namespace='monitoring')),
    path('programs/', include(('programs.urls', 'programs'), namespace='programs')),
    path('reports/', include(('reports.urls', 'reports'), namespace='reports')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)