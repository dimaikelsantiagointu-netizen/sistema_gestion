from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView # 👈 Importa TemplateView

urlpatterns = [
    # URLs de Administración de Django
    path('admin/', admin.site.urls),
    
    # URL de la Aplicación Recibos (Namespace: 'recibos')
    path('recibos/', include('apps.recibos.urls')), 
    
    # 🎯 NUEVA URL RAÍZ: Servir directamente el base.html
    # Asume que tu archivo está en: /templates/base.html (si esa es la ubicación registrada en settings.py)
    path('', TemplateView.as_view(template_name='base.html'), name='home'),
]