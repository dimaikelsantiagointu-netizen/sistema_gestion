from django.urls import path
from . import views
from .views import *

app_name = 'bienes'

urlpatterns = [
    # DASHBOARD PRINCIPAL DEL MÓDULO (Punto de entrada)
    # Al entrar a /bienes/ verás el panel con las opciones de Inventario, Carga Masiva, etc.
    path('', views.BienesDashboardView.as_view(), name='dashboard'),

    # ==========================
    # URLS DE BIENES
    # ==========================
    path('listar/', BienListView.as_view(), name='bien_list'),
    path('crear/', BienCreateView.as_view(), name='bien_create'),
    path('editar/<int:pk>/', BienUpdateView.as_view(), name='bien_update'),
    
    # Generación de etiquetas QR
    path('etiqueta/<int:pk>/', generar_etiqueta, name='generar_etiqueta'),

    # Carga masiva (RF-02)
    path('carga-masiva/', carga_masiva_bienes, name='carga_masiva'),

    # ==========================
    # URLS DE EMPLEADOS (Responsables)
    # ==========================
    path('empleados/', EmpleadoListView.as_view(), name='empleado_list'),
    path('empleados/crear/', EmpleadoCreateView.as_view(), name='empleado_create'),
    path('empleados/editar/<str:pk>/', EmpleadoUpdateView.as_view(), name='empleado_update'),

    # ==========================
    # URLS PÚBLICAS (Sin necesidad de login)
    # ==========================
    # Esta es la URL que se codifica en el código QR 
    path('consulta/<uuid:uuid>/', consulta_publica, name='consulta_publica'),



    path('estadisticas/', views.EstadisticasView.as_view(), name='estadisticas'),


    path('detalle/<int:pk>/', views.BienDetailView.as_view(), name='bien_detail'),
    
    # Historial de movimientos (RF-05 / BR-03)
    path('historial/<int:pk>/', views.BienHistorialView.as_view(), name='bien_historial'),

    path('unidades/nueva/', views.UnidadTrabajoCreateView.as_view(), name='unidad_create'),


    path('geografia/gestion/', views.GestionGeograficaView.as_view(), name='geografia_gestion'),
    path('region/nueva/', views.RegionCreateView.as_view(), name='region_create'),

    path('geografia/region/crear/', views.RegionCreateView.as_view(), name='region_create'),
    path('geografia/estado/crear/', views.EstadoCreateView.as_view(), name='estado_create'),
    path('geografia/municipio/crear/', views.MunicipioCreateView.as_view(), name='municipio_create'),
    path('geografia/ciudad/crear/', views.CiudadCreateView.as_view(), name='ciudad_create'),
    path('geografia/parroquia/crear/', views.ParroquiaCreateView.as_view(), name='parroquia_create'),



    # urls.py de la app bienes
path('ajax/load-parroquias/', views.load_parroquias, name='ajax_load_parroquias'),
]


