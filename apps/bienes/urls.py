from django.urls import path
from . import views
from .views import *

app_name = 'bienes'

urlpatterns = [

    # urls de empleados
    path('empleados/', EmpleadoListView.as_view(), name='empleado_list'),
    path('empleados/crear/', EmpleadoCreateView.as_view(), name='empleado_create'),
    path('empleados/editar/<str:pk>/', EmpleadoUpdateView.as_view(), name='empleado_update'),

    # urls de bienes
    path('bienes/', BienListView.as_view(), name='bien_list'),
    path('bienes/crear/', BienCreateView.as_view(), name='bien_create'),
    path('bienes/editar/<int:pk>/', BienUpdateView.as_view(), name='bien_update'),

    # urls de vista publica
    path('consulta/<uuid:uuid>/', consulta_publica, name='consulta_publica'),

    # urls de generación de etiquetas QR
    path('bienes/etiqueta/<int:pk>/', generar_etiqueta, name='generar_etiqueta'),

    # urls de carga masiva
    path('bienes/carga-masiva/', carga_masiva_bienes, name='carga_masiva'),



]