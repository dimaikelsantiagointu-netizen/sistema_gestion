# apps/recibos/urls.py

from django.urls import path

# 🚨 CAMBIO CRÍTICO: Importación explícita de CLASES
from apps.recibos.views import (
    ReciboListView,
    ReciboUpdateView,
    AnularReciboView,
    GenerarPdfView,
    ExcelUploadView,
    ReporteGeneracionView,
    ReciboCreateView
)

# Definición del 'namespace' para la aplicación
app_name = 'recibos' 

urlpatterns = [
    
    # Ya no usa 'views.', sino la clase directamente
    path('', ReciboListView.as_view(), name='recibo_list'), 
    path('<int:pk>/editar/', ReciboUpdateView.as_view(), name='recibo_edit'),
    path('<int:pk>/anular/', AnularReciboView.as_view(), name='recibo_anular'),
    path('<int:pk>/pdf/', GenerarPdfView.as_view(), name='recibo_pdf'),
    path('upload/', ExcelUploadView.as_view(), name='excel_upload'),
    path('reportes/', ReporteGeneracionView.as_view(), name='reporte_generacion'),
    path('crear/', ReciboCreateView.as_view(), name='recibo_create'),
]