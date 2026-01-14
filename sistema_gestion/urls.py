from django.contrib import admin
from django.urls import path, include
from apps.users.views import DashboardView

urlpatterns = [
    # 1. Administración
    path('admin/', admin.site.urls),
    
    # 2. Autenticación (Maneja login, logout, password_change, etc.)
    # Esto busca automáticamente templates/registration/login.html
    path('accounts/', include('django.contrib.auth.urls')),
    
    # 3. El Dashboard (Tu pantalla principal con base.html)
    # Esta debe ser la URL principal tras el login
    path('', DashboardView.as_view(), name='home'),
    
    # 4. Aplicaciones del sistema
    path('recibos/', include('apps.recibos.urls', namespace='recibos')),
    
]