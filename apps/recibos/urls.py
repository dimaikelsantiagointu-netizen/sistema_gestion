from django.urls import path
from . import views

app_name = 'recibos'

urlpatterns = [
    # Esta ruta es necesaria para que /recibos/ funcione
    path('', views.dashboard, name='index'), 
    

]