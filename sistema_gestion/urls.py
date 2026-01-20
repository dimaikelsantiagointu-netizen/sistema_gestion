from django.contrib import admin
from django.urls import path, include
from apps.users.views import DashboardView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 1. Administración
    path('admin/', admin.site.urls),
    
    # 2. Autenticación
    path('accounts/', include('django.contrib.auth.urls')),
    
    # 3. El Dashboard (Home)
    path('', DashboardView.as_view(), name='home'),
    
    # 4. Aplicaciones del sistema
    path('users/', include('apps.users.urls', namespace='users')),
    path('recibos/', include('apps.recibos.urls', namespace='recibos')),
    
    # 5. Gestión de Beneficiarios (AGREGAR ESTA LÍNEA)
    path('beneficiarios/', include('apps.beneficiarios.urls', namespace='beneficiarios')),

] 

# 6. Configuración para archivos media (Expedientes Digitales)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)