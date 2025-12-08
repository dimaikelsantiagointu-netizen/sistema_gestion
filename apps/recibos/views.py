from django.shortcuts import render, redirect
from django.contrib import messages
from .utils import importar_recibos_desde_excel 
# from .models import Recibo # (Si necesitas Recibo para otras cosas en la vista)

def dashboard(request):
    # Lógica de tu vista
    return render(request, 'recibos/dashboard.html', {})

def excel_upload_view(request):
    """Maneja la carga del archivo y llama a la lógica de importación."""
    
    # 1. Sólo procesamos si el método es POST y se subió un archivo
    if request.method == 'POST' and 'excel_file' in request.FILES:
        
        # El nombre 'excel_file' debe coincidir con el 'name' del input en tu formulario HTML
        excel_file = request.FILES['excel_file']
        
        # Validación básica del tipo de archivo
        if not excel_file.name.endswith(('.xlsx', '.xls')):
            messages.error(request, 'El archivo debe ser un formato Excel (.xlsx o .xls).')
            return redirect('recibos:tu_dashboard_url') # Reemplaza con tu URL de destino

        # 2. Llamar a la función de lógica y obtener el resultado
        success, message = importar_recibos_desde_excel(excel_file)
        
        # 3. Mostrar el resultado al usuario
        if success:
            messages.success(request, message)
        else:
            # messages.error es útil para mostrar el error de columna o el error general
            messages.error(request, f"Fallo en la carga: {message}")
            
        return redirect('recibos:dashboard') # Reemplaza con tu URL de destino
        
    # Si es un método GET, simplemente renderiza la plantilla principal
    # (Asegúrate de pasar el contexto necesario para que la plantilla funcione)
    return render(request, 'recibos/dashboard.html', {})