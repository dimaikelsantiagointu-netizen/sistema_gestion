# apps/recibos/urls.py

from django.urls import path
from . import views

# 🛑 ELIMINA O COMENTA ESTA LÍNEA INCORRECTA 🛑
# from .views import home_view # Vista que renderiza base.html 

app_name = 'recibos'

urlpatterns = [
    # 1. RUTA PRINCIPAL DE LA APP RECIBOS
    path('', views.dashboard, name='dashboard'), 
    
    # 2. RUTA DE PROCESAMIENTO
    path('upload/', views.excel_upload_view, name='upload_excel'),
    
]