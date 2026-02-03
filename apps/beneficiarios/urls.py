from django.urls import path
from . import views

app_name = 'beneficiarios'

urlpatterns = [
    # --- Gestión ---
    path('', views.lista_beneficiarios, name='lista'),
    path('nuevo/', views.crear_beneficiario, name='crear'),
    path('editar/<int:id>/', views.editar_beneficiario, name='editar'),
    path('eliminar/<int:id>/', views.eliminar_beneficiario, name='eliminar'),
    
    # --- Expediente (Documentos) ---
    path('expediente/<int:id>/', views.expediente_beneficiario, name='expediente'),
    path('expediente/documento/eliminar/<int:doc_id>/', views.eliminar_documento, name='eliminar_documento'),

    # --- Visitas (Historial) ---
    path('visitas/registrar/', views.registrar_visita, name='registrar_visita'),
    # AQUÍ LA CORRECCIÓN: Usamos views.detalle_beneficiario
    path('historial/<int:id>/', views.detalle_beneficiario, name='detalle'), 

    # --- Reportes y API ---
    path('exportar/excel/', views.exportar_excel, name='exportar_excel'),
    path('api/buscar/', views.buscar_beneficiario_api, name='buscar_api'),
]