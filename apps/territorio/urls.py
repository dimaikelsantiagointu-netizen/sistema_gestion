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
    # Usamos las funciones api_get_... que ya tienes en tus views
    path('ajax/municipios/<int:estado_id>/', views.api_get_municipios, name='ajax_load_municipios'),
    path('ajax/ciudades/<int:estado_id>/', views.api_get_ciudades, name='ajax_load_ciudades'),
    path('ajax/parroquias/<int:municipio_id>/', views.api_get_parroquias, name='ajax_load_parroquias'),
    path('ajax/comunas/<int:parroquia_id>/', views.api_get_comunas, name='ajax_load_comunas'),
]