from django.contrib import admin
from django.urls import path, include
from apps.users.views import DashboardView

urlpatterns = [
    # 1. Administración
    path('admin/', admin.site.urls),
    
    # 2. Autenticación
    path('accounts/', include('django.contrib.auth.urls')),
    
    # 3. El Dashboard (Home)
    path('', DashboardView.as_view(), name='home'),
    
    # 4. Aplicaciones del sistema
    path('users/', include('apps.users.urls', namespace='users')), # <-- AGREGA ESTA LÍNEA
    path('recibos/', include('apps.recibos.urls', namespace='recibos')),
]