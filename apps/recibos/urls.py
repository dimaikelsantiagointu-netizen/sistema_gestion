from django.urls import path
from . import views

app_name = 'recibos'

urlpatterns = [
    
    path('', views.crear_recibo_desde_excel, name='dashboard'),
    
    #nuevas agregadas
    path('reporte/', views.generar_reporte_view, name='generar_reporte'),
    #path('', views.dashboard_view, name='dashboard'),
    #path('reporte/', views.generar_reporte_view, name='generar_reporte'),
    #path('limpiar-logs/', views.limpiar_logs_view, name='limpiar_logs'),
]
