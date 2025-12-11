from django.urls import path
from . import views

# El App Name es crucial para usar {% url 'recibos:...' %} en las plantillas (como dashboard.html)
app_name = 'recibos'

urlpatterns = [
    # 1. Dashboard Principal (Filtro, Búsqueda, Paginación, Carga Excel, Anulación)
    path(
        '', 
        views.dashboard_view, 
        name='dashboard'
    ),

    # 2. Generación de Reportes Masivos (Llamada por los botones Excel/PDF del dashboard)
    # Esta vista recibe los filtros GET y devuelve el archivo
    path(
        'generar-reporte/', 
        views.generar_reporte_view, 
        name='generar_reporte'
    ),

    # 3. Flujo de Descarga Individual de PDF (Paso Intermedio)
    # Se utiliza después de una carga exitosa para iniciar la descarga del nuevo recibo.
    path(
        'descargar-init/<int:pk>/',
        views.init_download_and_refresh,
        name='init_download'
    ),

    # 4. Generación y Envío del PDF Individual Puro
    # Es la URL que la función JS en 'download_init.html' llama para obtener el archivo.
    path(
        'generar-pdf/<int:pk>/',
        views.generar_pdf_recibo,
        name='generar_pdf_recibo'
    ),
    
    # NOTA: La URL 'generar_pdf_reporte' de utils.py NO necesita una ruta aquí
    # porque es una función de utilidad que se llama desde la vista 'generar_reporte_view'.
]