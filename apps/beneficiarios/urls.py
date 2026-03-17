from django.urls import path
from . import views
from apps.territorio import views as territorio_views # <--- IMPORTANTE: Importar las vistas de territorio

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
    path('historial/<int:id>/', views.detalle_beneficiario, name='detalle'), 

    # --- Reportes y API ---
    path('exportar/excel/', views.exportar_excel, name='exportar_excel'),
    path('api/buscar/', views.buscar_beneficiario_api, name='buscar_api'),
    
    # -- RUTAS PARA CARGA DINÁMICA (Cambiamos "views" por "territorio_views") ---
    path('api/territorio/municipios/<int:estado_id>/', territorio_views.api_get_municipios, name='api_municipios'),
    path('api/territorio/ciudades/<int:estado_id>/', territorio_views.api_get_ciudades, name='api_ciudades'),
    path('api/territorio/parroquias/<int:municipio_id>/', territorio_views.api_get_parroquias, name='api_parroquias'),
    path('api/territorio/comunas/<int:parroquia_id>/', territorio_views.api_get_comunas, name='api_comunas'),   
    
    path('api/check-documento/', views.check_documento, name='check_documento'),


    path('gestion-documental/', views.gestion_documental, name='gestion_documental'),
    path('expediente/<int:pk>/', views.expediente_detalle, name='expediente'),

    path('estadisticas/', views.beneficiarios_estadisticas, name='estadisticas'),

]