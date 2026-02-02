# apps/contratos/urls.py
from django.urls import path
from . import views

app_name = 'contratos'

urlpatterns = [
    path('lista/', views.lista_contratos, name='lista'),
    path('crear/', views.crear_contrato, name='crear'),
    path('detalle/<int:pk>/', views.detalle_contrato, name='detalle'),
    
    # Ajustado para coincidir con el nombre en views.py
    path('descargar/<int:pk>/', views.descargar_pdf, name='descargar_pdf'),
    
    # Ajustado para coincidir con el nombre en views.py
    path('reporte/excel/', views.exportar_excel, name='exportar_excel'),
    
    # Si no tienes la función de estadísticas aún, puedes comentarla 
    # para que no te de error al arrancar:
    path('estadisticas/', views.estadisticas_contratos, name='estadisticas'),
    path('importar/', views.importar_contrato_existente, name='importar_existente'),
]