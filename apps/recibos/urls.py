from django.urls import path
from . import views 
from apps.recibos.views import PaginaBaseView
from .views import generar_zip_recibos
app_name = 'recibos'

urlpatterns = [
    path('', views.ReciboListView.as_view(),  name='dashboard' ),

    path('generar-reporte/',  views.generar_reporte_view,  name='generar_reporte' ),
   

    path( 'generar-pdf/<int:pk>/',views.generar_pdf_recibo,name='generar_pdf_recibo' ),
    
    path('modificar/<int:pk>/', views.modificar_recibo, name='modificar_recibo'),

    path('anulados/', views.recibos_anulados, name='recibos_anulados'), 
    path('', PaginaBaseView.as_view(), name='base'),
    path('generar-zip-recibos/', views.generar_zip_recibos, name='generar_zip_recibos'),
    path('estadisticas/', views.estadisticas_view, name='estadisticas'),
]