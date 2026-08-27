from django.urls import path
from . import views

app_name = 'sellos'

urlpatterns = [
    path('', views.SelloDoradoListView.as_view(), name='lista'),
    path('panel/', views.PanelConsultoriaView.as_view(), name='panel_consultoria'),
    path('crear/', views.SelloDoradoCreateView.as_view(), name='crear'),
    path('administracion/', views.AdministracionRecibosView.as_view(), name='administracion'),
    path('aprobar/', views.aprobar_recibos_view, name='aprobar_recibos'),
    path('asignar/', views.asignar_recibos_view, name='asignar_recibos'),
    path('marcar_leidos/', views.marcar_recibos_leidos_view, name='marcar_leidos'),
    path('export/', views.export_recibos_csv, name='export_recibos'),
    path('<int:pk>/imprimir/', views.imprimir_sello_view, name='imprimir'),
    path('<int:pk>/', views.SelloDoradoDetailView.as_view(), name='detalle'),
    path('<int:pk>/estatus/', views.cambiar_estatus_sello_view, name='cambiar_estatus'),
]
