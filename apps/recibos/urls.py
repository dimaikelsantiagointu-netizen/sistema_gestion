from django.urls import path
from . import views

app_name = 'recibos'

urlpatterns = [
    
    path('', views.crear_recibo_desde_excel, name='dashboard'),
]
