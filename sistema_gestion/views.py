from django.shortcuts import render

def home_view(request):
    """
    Vista que renderiza la plantilla base.html.
    Esto cumple con el requisito de cargar el layout principal al inicio.
    """
    # La función render busca 'base.html' en la carpeta 'templates' del proyecto
    return render(request, 'base.html', {})