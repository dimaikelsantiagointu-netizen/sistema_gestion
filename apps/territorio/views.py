from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required  # Importación de seguridad
from .models import Estado, Municipio, Ciudad, Parroquia, Comuna

# --- VISTA PRINCIPAL DEL PANEL ---
@login_required
def infraestructura_geografica(request):
    context = {
        'estados': Estado.objects.all().order_by('nombre'),
        'municipios': Municipio.objects.all().order_by('nombre'),
        'ciudades': Ciudad.objects.all().order_by('nombre'),
        'parroquias': Parroquia.objects.all().order_by('nombre'),
        'comunas': Comuna.objects.all().order_by('nombre'),
    }
    return render(request, 'territorio/territorio_admin.html', context)

# --- VISTAS DE CREACIÓN (PROTEGIDAS) ---

@login_required
def estado_create(request):
    if request.method == "POST":
        nombre = request.POST.get('nombre', '').strip().upper()
        if nombre:
            Estado.objects.create(nombre=nombre)
            messages.success(request, f"Estado {nombre} creado con éxito.")
        else:
            messages.error(request, "El nombre del estado es obligatorio.")
    return redirect('territorio:infraestructura')

@login_required
def municipio_create(request):
    if request.method == "POST":
        nombre = request.POST.get('nombre', '').strip().upper()
        estado_id = request.POST.get('parent_id') 
        
        if nombre and estado_id:
            Municipio.objects.create(nombre=nombre, estado_id=estado_id)
            messages.success(request, f"Municipio {nombre} registrado.")
        else:
            messages.error(request, "Faltan datos para registrar el municipio.")
    return redirect('territorio:infraestructura')

@login_required
def ciudad_create(request):
    if request.method == "POST":
        nombre = request.POST.get('nombre', '').strip().upper()
        estado_id = request.POST.get('parent_id')
        
        if nombre and estado_id:
            Ciudad.objects.create(nombre=nombre, estado_id=estado_id)
            messages.success(request, f"Ciudad {nombre} registrada.")
        else:
            messages.error(request, "Faltan datos para registrar la ciudad.")
    return redirect('territorio:infraestructura')

@login_required
def parroquia_create(request):
    if request.method == "POST":
        nombre = request.POST.get('nombre', '').strip().upper()
        municipio_id = request.POST.get('parent_id')
        
        if nombre and municipio_id:
            Parroquia.objects.create(nombre=nombre, municipio_id=municipio_id)
            messages.success(request, f"Parroquia {nombre} registrada.")
        else:
            messages.error(request, "Faltan datos para registrar la parroquia.")
    return redirect('territorio:infraestructura')

@login_required
def comuna_create(request):
    if request.method == "POST":
        nombre = request.POST.get('nombre', '').strip().upper()
        parroquia_id = request.POST.get('parent_id')
        
        if nombre and parroquia_id:
            Comuna.objects.create(
                nombre=nombre, 
                parroquia_id=parroquia_id
            )
            messages.success(request, f"Comuna {nombre} registrada correctamente.")
        else:
            messages.error(request, "Faltan datos para registrar la comuna.")
            
    return redirect('territorio:infraestructura')

# --- VISTAS API AJAX (PROTEGIDAS) ---
# Es vital protegerlas para evitar que scripts externos consulten tu estructura territorial

@login_required
def api_get_municipios(request, estado_id):
    data = Municipio.objects.filter(estado_id=estado_id).values('id', 'nombre').order_by('nombre')
    return JsonResponse(list(data), safe=False)

@login_required
def api_get_ciudades(request, estado_id):
    data = Ciudad.objects.filter(estado_id=estado_id).values('id', 'nombre').order_by('nombre')
    return JsonResponse(list(data), safe=False)

@login_required
def api_get_parroquias(request, municipio_id):
    data = Parroquia.objects.filter(municipio_id=municipio_id).values('id', 'nombre').order_by('nombre')
    return JsonResponse(list(data), safe=False)

@login_required
def api_get_comunas(request, parroquia_id):
    data = Comuna.objects.filter(parroquia_id=parroquia_id).values('id', 'nombre').order_by('nombre')
    return JsonResponse(list(data), safe=False)