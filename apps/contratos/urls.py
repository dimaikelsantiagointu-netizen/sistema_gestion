from django.urls import path
from . import views

app_name = 'contratos'

urlpatterns = [
    path('lista/', views.lista_contratos, name='lista'),
    path('crear/', views.crear_contrato, name='crear'),
    path('detalle/<int:pk>/', views.detalle_contrato, name='detalle'),
    
    path('historial/<int:pk>/', views.historial_contrato_view, name='historial'),
    
    path('descargar/<int:pk>/', views.descargar_pdf, name='descargar_pdf'),
    path('reporte/excel/', views.exportar_excel, name='exportar_excel'),
    
    path('estadisticas/', views.estadisticas_contratos, name='estadisticas'),
    
    path('importar/', views.importar_contrato_existente, name='importar_existente'),
]