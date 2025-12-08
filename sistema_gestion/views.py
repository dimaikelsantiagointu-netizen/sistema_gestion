from django.shortcuts import render

def home_view(request):

    # La función render busca 'base.html' en la carpeta 'templates' del proyecto
    return render(request, 'base.html', {})