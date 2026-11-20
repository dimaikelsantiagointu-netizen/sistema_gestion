from django.urls import path

from . import views

app_name = 'gestion_documental'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('expedientes/', views.lista_expedientes, name='lista'),
    path('expedientes/nuevo/', views.crear_expediente, name='crear'),
    path('expedientes/<int:pk>/', views.detalle_expediente, name='detalle'),
    path('expedientes/<int:pk>/editar/', views.editar_expediente, name='editar'),
    path(
        'expedientes/<int:pk>/archivos/<int:archivo_id>/descargar/',
        views.descargar_archivo,
        name='descargar_archivo',
    ),
    path(
        'expedientes/<int:pk>/archivos/<int:archivo_id>/eliminar/',
        views.eliminar_archivo,
        name='eliminar_archivo',
    ),
    path('titulares/', views.lista_titulares, name='titulares'),
    path('titulares/nuevo/', views.crear_titular, name='crear_titular'),
    path('titulares/<int:pk>/editar/', views.editar_titular, name='editar_titular'),
    path('estatus/', views.lista_estatus, name='estatus'),
    path('estatus/nuevo/', views.crear_estatus, name='crear_estatus'),
    path('estatus/<int:pk>/editar/', views.editar_estatus, name='editar_estatus'),
    path('estatus/<int:pk>/eliminar/', views.eliminar_estatus, name='eliminar_estatus'),
    path(
        'api/municipios/<int:estado_id>/',
        views.api_municipios,
        name='api_municipios',
    ),
    path(
        'api/parroquias/<int:municipio_id>/',
        views.api_parroquias,
        name='api_parroquias',
    ),
    path(
        'api/comunas/<int:parroquia_id>/',
        views.api_comunas,
        name='api_comunas',
    ),
]
