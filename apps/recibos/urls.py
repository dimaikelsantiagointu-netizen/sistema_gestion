from django.urls import path
from . import views

urlpatterns = [
    # Ruta principal para cargar el archivo Excel. Requiere login.
    path('upload/', views.upload_file_view, name='upload_file'),
    
    # Ruta para listar todos los recibos.
    path('receipts/', views.receipt_list_view, name='receipt_list'),
    
    # Ruta para generar el PDF de un recibo específico por su ID.
    path('receipts/pdf/<int:receipt_id>/', views.generate_pdf_view, name='generate_pdf'),
]