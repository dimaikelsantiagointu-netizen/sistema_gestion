from django.urls import path
from . import views

app_name = 'beneficiarios'

urlpatterns = [
    path('', views.lista_beneficiarios, name='lista'),
    path('expediente/<int:beneficiario_id>/', views.expediente_beneficiario, name='expediente'),
    path('documento/eliminar/<int:doc_id>/', views.eliminar_documento, name='eliminar_documento'),
    # Estas las crearemos a continuación:
    path('nuevo/', views.crear_beneficiario, name='crear'),
    path('editar/<int:id>/', views.editar_beneficiario, name='editar'),
    path('eliminar/<int:id>/', views.eliminar_beneficiario, name='eliminar'),
]