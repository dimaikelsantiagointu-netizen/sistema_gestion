from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    # URLs de Administración de Django
    path('admin/', admin.site.urls),
    
    # URL de la Aplicación Recibos
    path('recibos/', include('apps.recibos.urls', namespace='recibos')),     
    
    # URL RAÍZ base.html
    path('', TemplateView.as_view(template_name='base.html'), name='base'),
]