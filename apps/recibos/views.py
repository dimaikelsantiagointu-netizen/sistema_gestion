# apps/recibos/views.py

from django.shortcuts import render
from django.http import HttpResponse

def dashboard(request):
    """
    Vista de marcador de posición para la ruta /recibos/.
    """
    # ----------------------------------------------------
    # Opción 1: Simplemente devuelve una respuesta de texto (Para probar que funciona)
    # return HttpResponse("<h1>Dashboard de Recibos Funcionando</h1>")
    
    # Opción 2: Renderiza una plantilla (Recomendado)
    # Debes crear el archivo templates/recibos/dashboard.html
    return render(request, 'recibos/dashboard.html', {})
    # ----------------------------------------------------