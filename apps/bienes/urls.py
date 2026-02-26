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
    # Esta es la URL que se codifica en el código QR (RF-05)
    path('consulta/<uuid:uuid>/', consulta_publica, name='consulta_publica'),
]