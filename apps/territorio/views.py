from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.generic import CreateView, ListView, UpdateView
from django.urls import reverse_lazy
from django.db.models import Count
from django.contrib.auth.mixins import LoginRequiredMixin
import logging

from .models import Estado, Municipio, Ciudad, Parroquia, Comuna, UnidadAdscrita
from .forms import UnidadAdscritaForm

logger_territorio = logging.getLogger('CH_TERRITORIO')

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

# --- VISTAS DE CREACIÓN (MANTENIENDO TU LÓGICA ORIGINAL) ---

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
            Comuna.objects.create(nombre=nombre, parroquia_id=parroquia_id)
            messages.success(request, f"Comuna {nombre} registrada correctamente.")
        else:
            messages.error(request, "Faltan datos para registrar la comuna.")
    return redirect('territorio:infraestructura')

# --- VISTAS API AJAX (CORREGIDAS PARA EL FORMULARIO DE PERSONAL) ---

@login_required
def api_get_municipios(request, estado_id=None):
    # Si no viene en la URL, lo buscamos en el parámetro GET (?estado_id=)
    if not estado_id:
        estado_id = request.GET.get('estado_id')
    
    data = Municipio.objects.filter(estado_id=estado_id).values('id', 'nombre').order_by('nombre')
    return JsonResponse(list(data), safe=False)

@login_required
def api_get_ciudades(request, estado_id=None):
    if not estado_id:
        estado_id = request.GET.get('estado_id')
        
    data = Ciudad.objects.filter(estado_id=estado_id).values('id', 'nombre').order_by('nombre')
    return JsonResponse(list(data), safe=False)

@login_required
def api_get_parroquias(request, municipio_id=None):
    if not municipio_id:
        municipio_id = request.GET.get('municipio_id')
        
    data = Parroquia.objects.filter(municipio_id=municipio_id).values('id', 'nombre').order_by('nombre')
    return JsonResponse(list(data), safe=False)

@login_required
def api_get_comunas(request, parroquia_id=None):
    if not parroquia_id:
        parroquia_id = request.GET.get('parroquia_id')
        
    data = Comuna.objects.filter(parroquia_id=parroquia_id).values('id', 'nombre').order_by('nombre')
    return JsonResponse(list(data), safe=False)

# --- GESTIÓN DE UNIDADES ADSCRITAS ---

class UnidadListView(LoginRequiredMixin, ListView):
    model = UnidadAdscrita
    template_name = 'territorio/unidades_list.html'
    context_object_name = 'unidades'

    def get_queryset(self):
        return UnidadAdscrita.objects.annotate(
            total_trabajadores=Count('personal_asignado')
        ).order_by('nombre')

class UnidadCreateView(LoginRequiredMixin, CreateView):
    model = UnidadAdscrita
    form_class = UnidadAdscritaForm
    template_name = 'territorio/unidad_form.html'
    success_url = reverse_lazy('territorio:unidades_lista')

    def form_valid(self, form):
        nombre = form.cleaned_data.get('nombre')
        response = super().form_valid(form)
        messages.success(self.request, "NUEVA UNIDAD REGISTRADA.")
        logger_territorio.info(f"CREATE_UNIDAD: {nombre} | BY: {self.request.user}")
        return response

class UnidadUpdateView(LoginRequiredMixin, UpdateView):
    model = UnidadAdscrita
    form_class = UnidadAdscritaForm
    template_name = 'territorio/unidad_form.html'
    success_url = reverse_lazy('territorio:unidades_lista')

    def form_valid(self, form):
        nombre = form.cleaned_data.get('nombre')
        response = super().form_valid(form)
        messages.info(self.request, "UNIDAD ACTUALIZADA CORRECTAMENTE.")
        logger_territorio.info(f"UPDATE_UNIDAD: {nombre} | BY: {self.request.user}")
        return response

@login_required
def eliminar_unidad(request, pk):
    unidad = get_object_or_404(UnidadAdscrita, pk=pk)
    try:
        nombre = unidad.nombre
        unidad.delete()
        messages.warning(request, f"UNIDAD {nombre} ELIMINADA.")
        logger_territorio.info(f"DELETE_UNIDAD: {nombre} | BY: {request.user}")
    except Exception as e:
        logger_territorio.error(f"ERROR_DELETE_UNIDAD: {str(e)}")
        messages.error(request, "NO SE PUEDE ELIMINAR: Esta unidad tiene personal asociado.")
    return redirect('territorio:unidades_lista')