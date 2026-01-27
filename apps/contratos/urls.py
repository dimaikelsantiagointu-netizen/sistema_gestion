# apps/contratos/urls.py
from django.urls import path
from . import views

app_name = 'contratos'

urlpatterns = [
    path('lista/', views.lista_contratos, name='lista'),
    path('crear/', views.crear_contrato, name='crear'),
    path('detalle/<int:pk>/', views.detalle_contrato, name='detalle'),
    path('descargar/<int:pk>/', views.descargar_contrato_pdf, name='descargar_pdf'),
    path('estadisticas/', views.estadisticas_contratos, name='estadisticas'),
    path('reporte/excel/', views.exportar_contratos_excel, name='exportar_excel'),
]