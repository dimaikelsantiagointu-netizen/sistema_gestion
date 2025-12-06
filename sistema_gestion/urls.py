from django.contrib import admin
from django.urls import path, include

# *****************************************************************
# IMPORTACIÓN DE LA NUEVA VISTA DE INICIO
# Se asume que esta vista está en el views.py del proyecto principal.
# *****************************************************************
from .views import home_view # Asegúrate de que este archivo exista

urlpatterns = [
    # *****************************************************************
    # 1. RUTA RAÍZ: CARGA LA VISTA HOME_VIEW (que renderizará base.html)
    # *****************************************************************
    path('', home_view, name='home'), 
    path('admin/', admin.site.urls),
    path('', include('django.contrib.auth.urls')),
    
   
    # -----------------------------------------------------------------
    path('recibos/', include('apps.recibos.urls', namespace='recibos')), 
    path('', include('django.contrib.auth.urls')),
    # *****************************************************************

    
]