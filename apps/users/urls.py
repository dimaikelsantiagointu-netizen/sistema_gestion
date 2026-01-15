from django.urls import path
from .views import DashboardView, CrearUsuarioView

# El app_name es vital para que {% url 'users:crear_usuario' %} funcione
app_name = 'users'

urlpatterns = [
    # Ruta para el home/dashboard de la aplicación
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    
    # Ruta para el formulario de registro que acabamos de crear
    path('crear/', CrearUsuarioView.as_view(), name='crear_usuario'),
]