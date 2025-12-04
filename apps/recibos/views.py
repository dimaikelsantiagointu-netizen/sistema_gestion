from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.contrib import messages
from django.db.models import Max # Importa Max para encontrar el último número de recibo

from .models import Receipt
from .forms import UploadFileForm
from .utils import clean, is_marked, format_date_for_db, generate_receipt_pdf
import pandas as pd
import io # Para manejar el archivo subido en memoria

# Número inicial para la secuencia de recibos si no hay ninguno en la DB
INITIAL_RECEIPT_NUMBER = 10000000

def get_next_receipt_number():
    """
    Calcula el siguiente número de recibo consecutivo.
    Busca el recibo más grande existente y le suma uno.
    """
    # Busca el valor máximo del campo receipt_number (convertido a entero para comparación)
    max_number_query = Receipt.objects.aggregate(Max('receipt_number'))['receipt_number__max']
    
    try:
        if max_number_query:
            # Si hay recibos, toma el máximo, lo convierte a int, y le suma 1.
            last_number = int(max_number_query)
            return str(last_number + 1)
        else:
            # Si es el primer recibo, usa el número inicial.
            return str(INITIAL_RECEIPT_NUMBER)
    except ValueError:
        # En caso de que un número no sea convertible a int (error de datos), 
        # se vuelve al número inicial o se lanza un error.
        return str(INITIAL_RECEIPT_NUMBER)

@login_required
def upload_file_view(request):
    """
    Vista para subir el archivo Excel y procesar los recibos.
    Permite la carga masiva y maneja las transacciones de base de datos.
    """
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['file']
            
            # 1. Cargar el archivo en memoria (BytesIO)
            file_data = io.BytesIO(excel_file.read())
            
            try:
                # 2. Leer el archivo Excel
                df = pd.read_excel(file_data, engine='openpyxl')
                # Renombrar columnas para facilitar el acceso
                df.columns = [
                    'Nº Recibo', 'Nº Transferencia', 'Fecha', 'RIF/C.I', 'Nombre', 
                    'Monto', 'Concepto', 'Dirección', 
                    'Cat1', 'Cat2', 'Cat3', 'Cat4', 'Cat5', 'Cat6', 'Cat7', 'Cat8', 'Cat9', 'Cat10'
                ]
                
                new_receipts = []
                # El procesamiento de la carga masiva debe ser atómico
                with transaction.atomic():
                    
                    # Obtener el primer número de recibo disponible antes de empezar el lote
                    current_receipt_number = int(get_next_receipt_number())

                    for index, row in df.iterrows():
                        # Generar el número de recibo consecutivo
                        receipt_num = str(current_receipt_number)
                        
                        # Mapeo y limpieza de datos usando las funciones de utils.py
                        data = {
                            'receipt_number': receipt_num,
                            'transaction_number': clean(row['Nº Transferencia']),
                            'payment_date': format_date_for_db(row['Fecha']),
                            'client_id': clean(row['RIF/C.I']),
                            'client_name': clean(row['Nombre']),
                            'amount': clean(row['Monto']).replace('.', '').replace(',', '.'), # Normalizar monto a formato flotante (XX.XX)
                            'concept': clean(row['Concepto']),
                            'client_address': clean(row['Dirección']),
                            'categoria1': is_marked(row['Cat1']),
                            'categoria2': is_marked(row['Cat2']),
                            'categoria3': is_marked(row['Cat3']),
                            'categoria4': is_marked(row['Cat4']),
                            'categoria5': is_marked(row['Cat5']),
                            'categoria6': is_marked(row['Cat6']),
                            'categoria7': is_marked(row['Cat7']),
                            'categoria8': is_marked(row['Cat8']),
                            'categoria9': is_marked(row['Cat9']),
                            'categoria10': is_marked(row['Cat10']),
                            'created_by': request.user, # Asignar al usuario logueado
                        }
                        
                        # Creación de la instancia del modelo Receipt
                        new_receipt = Receipt(**data)
                        new_receipts.append(new_receipt)
                        
                        # Incrementar el número de recibo para el siguiente registro
                        current_receipt_number += 1

                    # Inserción masiva en la base de datos (más eficiente)
                    Receipt.objects.bulk_create(new_receipts)
                
                messages.success(request, f'Se procesaron y guardaron {len(new_receipts)} recibos exitosamente.')
                return redirect('receipt_list')

            except Exception as e:
                # Manejo de errores durante el procesamiento (ej. formato de Excel incorrecto)
                messages.error(request, f'Error al procesar el archivo: {e}')
                return render(request, 'recibos/upload.html', {'form': form})
    else:
        # Si el método es GET, muestra el formulario de carga
        form = UploadFileForm()
    
    return render(request, 'recibos/upload.html', {'form': form})


@login_required
def receipt_list_view(request):
    """
    Vista para listar todos los recibos.
    """
    # Filtra los recibos creados por el usuario actual o muestra todos si es superusuario
    if request.user.is_superuser:
        receipts = Receipt.objects.all()
    else:
        receipts = Receipt.objects.filter(created_by=request.user)
    
    # Se pasa la lista de recibos al template para ser renderizada
    return render(request, 'recibos/receipt_list.html', {'receipts': receipts})


@login_required
def generate_pdf_view(request, receipt_id):
    """
    Vista para generar y descargar el archivo PDF de un recibo específico.
    Reemplaza la lógica de llamada a pdf_generator.py.
    """
    # Obtiene el recibo por ID o lanza 404
    receipt = get_object_or_404(Receipt, pk=receipt_id)
    
    # Restricción de seguridad: Solo el creador o un superusuario pueden descargar el PDF
    if receipt.created_by != request.user and not request.user.is_superuser:
        messages.error(request, "No tiene permiso para descargar este recibo.")
        return redirect('receipt_list')

    try:
        # Llama a la función de utilidad para generar el PDF en memoria (BytesIO)
        pdf_buffer = generate_receipt_pdf(receipt)
        
        # Configura la respuesta HTTP para devolver el archivo PDF
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        filename = f'Recibo_{receipt.receipt_number}.pdf'
        # Indica al navegador que descargue el archivo
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    except Exception as e:
        messages.error(request, f"Error al generar el PDF: {e}")
        return redirect('receipt_list')