# Sistema_gestion-main/urls.py

from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView # 👈 Correcto: usar TemplateView directamente

urlpatterns = [
    # URLs de Administración de Django
    path('admin/', admin.site.urls),
    
    # URL de la Aplicación Recibos (Namespace: 'recibos')
    path('recibos/', include('apps.recibos.urls', namespace='recibos')),     
    
    # 🎯 URL RAÍZ CORREGIDA: Servir base.html con el nombre 'base'
    path('', TemplateView.as_view(template_name='base.html'), name='base'), # <-- ¡CAMBIADO a name='base'!
]