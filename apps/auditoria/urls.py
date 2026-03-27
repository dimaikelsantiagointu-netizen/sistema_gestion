from django.urls import path
from . import views

app_name = 'auditoria'

urlpatterns = [
    # Vista principal de la bitácora
    path('bitacora/', views.lista_auditoria, name='ver_bitacora'),
    
    # Rutas para generación de reportes (Punto 5 de requerimientos)
    path('exportar/excel/', views.exportar_auditoria_excel, name='exportar_excel'),
    path('exportar/pdf/', views.exportar_auditoria_pdf, name='exportar_pdf'),
    path('dashboard/', views.estadisticas_auditoria, name='estadisticas_auditoria'),
]