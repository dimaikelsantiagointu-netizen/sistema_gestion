from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from .models import Estado, Municipio, Ciudad, Parroquia, Comuna

# --- VISTA PRINCIPAL DEL PANEL ---
def infraestructura_geografica(request):
    context = {
        'estados': Estado.objects.all().order_by('nombre'),
        'municipios': Municipio.objects.all().order_by('nombre'),
        'ciudades': Ciudad.objects.all().order_by('nombre'),
        'parroquias': Parroquia.objects.all().order_by('nombre'),
        'comunas': Comuna.objects.all().order_by('nombre'),
    }
    return render(request, 'territorio/territorio_admin.html', context)

# --- VISTAS DE CREACIÓN (Para los Modales) ---

def estado_create(request):
    if request.method == "POST":
        nombre = request.POST.get('nombre')
        Estado.objects.create(nombre=nombre)
        messages.success(request, f"Estado {nombre} creado con éxito.")
    return redirect('territorio:infraestructura')

def municipio_create(request):
    if request.method == "POST":
        nombre = request.POST.get('nombre')
        estado_id = request.POST.get('parent') # En el script name="estado" o "parent"
        estado = Estado.objects.get(id=estado_id)
        Municipio.objects.create(nombre=nombre, estado=estado)
        messages.success(request, f"Municipio {nombre} registrado.")
    return redirect('territorio:infraestructura')

def ciudad_create(request):
    if request.method == "POST":
        nombre = request.POST.get('nombre')
        estado_id = request.POST.get('parent')
        estado = Estado.objects.get(id=estado_id)
        Ciudad.objects.create(nombre=nombre, estado=estado)
        messages.success(request, f"Ciudad {nombre} registrada.")
    return redirect('territorio:infraestructura')

def parroquia_create(request):
    if request.method == "POST":
        nombre = request.POST.get('nombre')
        municipio_id = request.POST.get('parent')
        municipio = Municipio.objects.get(id=municipio_id)
        Parroquia.objects.create(nombre=nombre, municipio=municipio)
        messages.success(request, f"Parroquia {nombre} registrada.")
    return redirect('territorio:infraestructura')

def comuna_create(request):
    if request.method == "POST":
        nombre = request.POST.get('nombre')
        codigo = request.POST.get('codigo_comuna')
        parroquia_id = request.POST.get('parent')
        parroquia = Parroquia.objects.get(id=parroquia_id)
        Comuna.objects.create(nombre=nombre, codigo_comuna=codigo, parroquia=parroquia)
        messages.success(request, f"Comuna {nombre} registrada correctamente.")
    return redirect('territorio:infraestructura')

# --- TUS VISTAS AJAX (Verificadas y funcionando) ---

def ajax_load_municipios(request):
    estado_id = request.GET.get('estado_id')
    municipios = Municipio.objects.filter(estado_id=estado_id).values('id', 'nombre').order_by('nombre')
    return JsonResponse(list(municipios), safe=False)

def ajax_load_ciudades(request):
    estado_id = request.GET.get('estado_id')
    ciudades = Ciudad.objects.filter(estado_id=estado_id).values('id', 'nombre').order_by('nombre')
    return JsonResponse(list(ciudades), safe=False)

def ajax_load_parroquias(request):
    municipio_id = request.GET.get('municipio_id')
    parroquias = Parroquia.objects.filter(municipio_id=municipio_id).values('id', 'nombre').order_by('nombre')
    return JsonResponse(list(parroquias), safe=False)

def ajax_load_comunas(request):
    parroquia_id = request.GET.get('parroquia_id')
    comunas = Comuna.objects.filter(parroquia_id=parroquia_id).values('id', 'nombre').order_by('nombre')
    return JsonResponse(list(comunas), safe=False)