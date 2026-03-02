from django.urls import path
from . import views
from .views import *

app_name = 'bienes'

urlpatterns = [
    # ==========================================
    # DASHBOARD Y VISTAS PRINCIPALES
    # ==========================================
    # Punto de entrada al módulo de bienes
    path('', views.BienesDashboardView.as_view(), name='dashboard'),
    
    # Listado general de inventario
    path('listar/', BienListView.as_view(), name='bien_list'),
    
    # Panel de estadísticas (Preferencia: No eliminar botón)
    path('estadisticas/', views.EstadisticasView.as_view(), name='estadisticas'),

    # ==========================================
    # GESTIÓN DE BIENES (CRUD Y HERRAMIENTAS)
    # ==========================================
    path('crear/', BienCreateView.as_view(), name='bien_create'),
    path('editar/<int:pk>/', BienUpdateView.as_view(), name='bien_update'),
    path('detalle/<int:pk>/', views.BienDetailView.as_view(), name='bien_detail'),
    
    # Historial de movimientos/contratos (En desarrollo)
    path('historial/<int:pk>/', views.BienHistorialView.as_view(), name='bien_historial'),
    
    # Etiquetas QR y Carga Masiva
    path('etiqueta/<int:pk>/', generar_etiqueta, name='generar_etiqueta'),
    path('carga-masiva/', carga_masiva_bienes, name='carga_masiva'),

    # ==========================================
    # GESTIÓN DE PERSONAL Y UNIDADES
    # ==========================================
    path('empleados/', EmpleadoListView.as_view(), name='empleado_list'),
    path('empleados/crear/', EmpleadoCreateView.as_view(), name='empleado_create'),
    path('empleados/editar/<str:pk>/', EmpleadoUpdateView.as_view(), name='empleado_update'),
    path('unidades/nueva/', views.UnidadTrabajoCreateView.as_view(), name='unidad_create'),

    # ==========================================
    # INFRAESTRUCTURA GEOGRÁFICA (VISTAS)
    # ==========================================
    # Panel principal de gestión geográfica
    path('geografia/gestion/', views.GestionGeograficaView.as_view(), name='geografia_gestion'),
    
    # Rutas para la creación de nuevos niveles geográficos (Modales/Formularios)
    path('geografia/region/crear/', views.RegionCreateView.as_view(), name='region_create'),
    path('geografia/estado/crear/', views.EstadoCreateView.as_view(), name='estado_create'),
    path('geografia/municipio/crear/', views.MunicipioCreateView.as_view(), name='municipio_create'),
    path('geografia/ciudad/crear/', views.CiudadCreateView.as_view(), name='ciudad_create'),
    path('geografia/parroquia/crear/', views.ParroquiaCreateView.as_view(), name='parroquia_create'),

    # ==========================================
    # SERVICIOS AJAX (FILTRADO EN CASCADA)
    # ==========================================
    # Estas rutas alimentan el Explorador Dinámico
    path('ajax/load-estados/', views.ajax_load_estados, name='ajax_load_estados'),
    path('ajax/load-municipios/', views.ajax_load_municipios, name='ajax_load_municipios'),
    path('ajax/load-ciudades/', views.ajax_load_ciudades, name='ajax_load_ciudades'),
    path('ajax/load-parroquias/', views.ajax_load_parroquias, name='ajax_load_parroquias'),
    
    # Carga de las tarjetas visuales finales en el explorador
    path('ajax/load-detalles/', views.ajax_load_detalles_finales, name='ajax_load_detalles_finales'),

    # ==========================================
    # CONSULTA PÚBLICA (ACCESO EXTERNO)
    # ==========================================
    # Acceso mediante QR sin necesidad de login
    path('consulta/<uuid:uuid>/', consulta_publica, name='consulta_publica'),
]