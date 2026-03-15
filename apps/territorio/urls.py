from django.urls import path
from . import views

app_name = 'territorio'

urlpatterns = [
    # Vista principal
    path('infraestructura/', views.infraestructura_geografica, name='infraestructura'),

    # URLs para creación (Modales)
    path('estado/create/', views.estado_create, name='estado_create'),
    path('municipio/create/', views.municipio_create, name='municipio_create'),
    path('ciudad/create/', views.ciudad_create, name='ciudad_create'),
    path('parroquia/create/', views.parroquia_create, name='parroquia_create'),
    path('comuna/create/', views.comuna_create, name='comuna_create'),

    # URLs para AJAX (Carga en cascada)
    path('ajax/municipios/', views.ajax_load_municipios, name='ajax_load_municipios'),
    path('ajax/ciudades/', views.ajax_load_ciudades, name='ajax_load_ciudades'),
    path('ajax/parroquias/', views.ajax_load_parroquias, name='ajax_load_parroquias'),
    path('ajax/comunas/', views.ajax_load_comunas, name='ajax_load_comunas'),
]