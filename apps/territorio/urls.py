from django.urls import path
from . import views

app_name = 'territorio'

urlpatterns = [
    # --- VISTA PRINCIPAL ---
    path('infraestructura/', views.infraestructura_geografica, name='infraestructura'),

    # --- CRUD (MODALES) ---
    path('estado/create/', views.estado_create, name='estado_create'),
    path('municipio/create/', views.municipio_create, name='municipio_create'),
    path('ciudad/create/', views.ciudad_create, name='ciudad_create'),
    path('parroquia/create/', views.parroquia_create, name='parroquia_create'),
    path('comuna/create/', views.comuna_create, name='comuna_create'),

    # --- CARGA DINÁMICA (API) ---
    # Nota: Registramos dos patrones para cada una para máxima compatibilidad
    
    # Municipios
    path('ajax/municipios/', views.api_get_municipios, name='ajax_municipios_base'), 
    path('ajax/municipios/<int:estado_id>/', views.api_get_municipios, name='ajax_load_municipios'),
    
    # Ciudades
    path('ajax/ciudades/', views.api_get_ciudades, name='ajax_ciudades_base'),
    path('ajax/ciudades/<int:estado_id>/', views.api_get_ciudades, name='ajax_load_ciudades'),
    
    # Parroquias
    path('ajax/parroquias/', views.api_get_parroquias, name='ajax_parroquias_base'),
    path('ajax/parroquias/<int:municipio_id>/', views.api_get_parroquias, name='ajax_load_parroquias'),
    
    # Comunas
    path('ajax/comunas/', views.api_get_comunas, name='ajax_comunas_base'),
    path('ajax/comunas/<int:parroquia_id>/', views.api_get_comunas, name='ajax_load_comunas'),

    # --- UNIDADES ADSCRITAS ---
    path('unidades/', views.UnidadListView.as_view(), name='unidades_lista'),
    path('unidades/nueva/', views.UnidadCreateView.as_view(), name='unidad_crear'),
    path('unidades/editar/<int:pk>/', views.UnidadUpdateView.as_view(), name='unidad_editar'),
    path('unidades/eliminar/<int:pk>/', views.eliminar_unidad, name='unidad_eliminar'),
]