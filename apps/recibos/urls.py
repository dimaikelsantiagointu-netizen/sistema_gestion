# apps/recibos/urls.py

from django.urls import path
from . import views

# Definición del 'namespace' para la aplicación
app_name = 'recibos' 

urlpatterns = [
    # 1. Dashboard / Listado Principal
    # Soluciona el AttributeError usando ReciboListView
    path('', views.ReciboListView.as_view(), name='recibo_list'), # Renombrado a 'recibo_list'
    
    
    # 3. Edición/Actualización de Recibo (Requiere PK)
    path('<int:pk>/editar/', views.ReciboUpdateView.as_view(), name='recibo_edit'),
    
    # 4. Anulación de Recibo (Requiere PK)
    path('<int:pk>/anular/', views.AnularReciboView.as_view(), name='recibo_anular'),
    
    # 5. Generación de PDF individual (Requiere PK)
    path('<int:pk>/pdf/', views.GenerarPdfView.as_view(), name='recibo_pdf'),
    
    # 6. Carga Masiva de Excel (Requiere permisos de Admin)
    path('upload/', views.ExcelUploadView.as_view(), name='excel_upload'),
    
    # 7. Generación de Reportes (Filtros, Excel/PDF)
    path('reportes/', views.ReporteGeneracionView.as_view(), name='reporte_generacion'),
]