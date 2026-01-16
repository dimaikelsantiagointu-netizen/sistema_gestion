from django.shortcuts import render

def home_view(request):
    # Ahora llamamos a gestores.html
    # Django automáticamente cargará base.html porque gestores.html tiene el {% extends %}
    return render(request, 'gestores.html', {})