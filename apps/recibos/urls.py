# apps/recibos/urls.py

from django.urls import path
from . import views

app_name = 'recibos'

urlpatterns = [
    # ----------------------------------------------------
    # CORRECCIÓN AQUÍ: Cambiamos 'crear_recibo_desde_excel' por 'dashboard_view'
    path('', views.dashboard_view, name='dashboard'), 
    
    # URL para descargar el PDF de un recibo específico
    path('recibo/<int:pk>/pdf/', views.generar_pdf_recibo, name='generar_pdf_recibo'), 
    
    # URL para la edición de recibos (asumiendo que ya tienes esta vista)
    # path('recibo/<int:pk>/editar/', views.editar_recibo, name='editar_recibo'), 
    
    # URL para generar reportes (Excel/PDF)
    path('reporte/', views.generar_reporte_view, name='generar_reporte'), 
    path('recibo/<int:pk>/download-init/', views.init_download_and_refresh, name='init_download'),
]