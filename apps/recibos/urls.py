# apps/recibos/urls.py

from django.urls import path
from . import views # Asegúrese de que views.py contenga la clase ReciboListView
from apps.recibos.views import PaginaBaseView
from .views import generar_zip_recibos
app_name = 'recibos'

urlpatterns = [
    # 1. Dashboard Principal
    # AHORA USA ReciboListView.as_view()
    path(
        '', 
        views.ReciboListView.as_view(), 
        name='dashboard'
    ),

    # 2. Generación de Reportes Masivos
    path(
        'generar-reporte/', 
        views.generar_reporte_view, 
        name='generar_reporte'
    ),

    # 3. Flujo de Descarga Individual de PDF 
    path(
        'descargar-init/<int:pk>/',
        views.init_download_and_refresh,
        name='init_download'
    ),

    # 4. Generación y Envío del PDF Individual Puro
    path(
        'generar-pdf/<int:pk>/',
        views.generar_pdf_recibo,
        name='generar_pdf_recibo'
    ),
    
    # 5. Modificación/Anulación de Recibo
    path('modificar/<int:pk>/', views.modificar_recibo, name='modificar_recibo'),

    # 💥 RUTA FALTANTE AGREGADA (Soluciona el NoReverseMatch)
    path('anulados/', views.recibos_anulados, name='recibos_anulados'), 
    path('', PaginaBaseView.as_view(), name='base'),
    path('generar-zip-recibos/', views.generar_zip_recibos, name='generar_zip_recibos'),
]