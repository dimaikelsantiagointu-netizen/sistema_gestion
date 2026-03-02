from django.views.generic import *
from django.urls import reverse_lazy
from .models import *
from .forms import *
from django.db.models import Q, Count, Sum
from django.shortcuts import render, get_object_or_404, redirect
import csv
import openpyxl
from django.db import transaction
from django.contrib import messages
import uuid
from django.http import HttpResponse, FileResponse, JsonResponse
import os
from .utils import *
from django.conf import settings


#==========================
# Vistas de empleados
# ==========================
class EmpleadoListView(ListView):
    model = Empleado
    template_name = 'bienes/empleados/listar.html'
    context_object_name = 'empleados'
    paginate_by = 10

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return Empleado.objects.filter(
                Q(nombre__icontains=query) |
                Q(apellido__icontains=query) |
                Q(cedula__icontains=query)
            )
        return Empleado.objects.all().order_by('apellido')


class EmpleadoCreateView(CreateView):
    model = Empleado
    form_class = EmpleadoForm
    template_name = 'bienes/empleados/crear.html'
    # CORRECCIÓN AQUÍ: Añadir 'bienes:'
    success_url = reverse_lazy('bienes:empleado_list') 

class EmpleadoUpdateView(UpdateView):
    model = Empleado
    form_class = EmpleadoForm
    template_name = 'bienes/empleados/crear.html'
    # CORRECCIÓN AQUÍ: Añadir 'bienes:'
    success_url = reverse_lazy('bienes:empleado_list')

#=========================
# VISTAS DE BIENES
# ==========================
class BienListView(ListView):
    model = BienNacional
    template_name = 'bienes/bienes/listar.html'
    context_object_name = 'bienes'
    paginate_by = 10
    ordering = ['-fecha_registro']


class BienCreateView(CreateView):
    model = BienNacional
    form_class = BienForm
    template_name = 'bienes/bienes/crear.html'
    success_url = reverse_lazy('bienes:bien_list')

class BienUpdateView(UpdateView):
    model = BienNacional
    form_class = BienForm
    template_name = 'bienes/bienes/crear.html'
    success_url = reverse_lazy('bienes:bien_list')

    def form_valid(self, form):
        bien = self.get_object()
        empleado_anterior = bien.empleado_uso
        empleado_nuevo = form.cleaned_data['empleado_uso']

        response = super().form_valid(form)

        if empleado_anterior != empleado_nuevo:
            MovimientoBien.objects.create(
                bien=bien,
                empleado_anterior=empleado_anterior,
                empleado_nuevo=empleado_nuevo,
                usuario_sistema=self.request.user.username
            )

        return response
    
# ==========================
# VISTAS PUBLICA
# ==========================


def consulta_publica(request, uuid):
    bien = get_object_or_404(BienNacional, uuid=uuid)

    context = {
        "descripcion": bien.descripcion,
        "marca": bien.marca,
        "modelo": bien.modelo,
        "serial": bien.serial,
        "estado": bien.estado_bien,
        "ciudad": bien.unidad_trabajo.ciudad.nombre,
        "unidad": bien.unidad_trabajo.nombre,
    }

    return render(request, "bienes/consulta_publica.html", context)


class BienDetailView(DetailView):
    model = BienNacional
    template_name = 'bienes/bienes/detalle.html'
    context_object_name = 'bien'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['historial'] = MovimientoBien.objects.filter(bien=self.object).order_by('-fecha')
        return context
    


# ==========================
# vista para generar PDF qr
# ==========================


def generar_etiqueta(request, pk):
    bien = get_object_or_404(BienNacional, pk=pk)
    pdf_buffer = generar_etiqueta_pdf(bien)
    
    response = FileResponse(
        pdf_buffer, 
        as_attachment=True, 
        filename=f"etiqueta_{bien.nro_identificacion}.pdf"
    )
    
    return response

def descargar_etiqueta(request, pk):
    return generar_etiqueta(request, pk)


# ==========================
# carga masiva de bienes MODIFICAR PARA EL FORMATO ACTUAL
# ==========================
def carga_masiva_bienes(request):

    if request.method == "POST":
        form = CargaMasivaForm(request.POST, request.FILES)

        if form.is_valid():
            archivo = request.FILES['archivo']
            errores = []
            bienes_crear = []

            try:
                if archivo.name.endswith('.xlsx'):
                    wb = openpyxl.load_workbook(archivo)
                    hoja = wb.active
                    filas = hoja.iter_rows(min_row=2, values_only=True)
                else:
                    decoded = archivo.read().decode('utf-8').splitlines()
                    reader = csv.reader(decoded)
                    next(reader)
                    filas = reader

                with transaction.atomic():

                    for fila in filas:
                        try:
                            (
                                nro_identificacion,
                                subcuenta,
                                descripcion,
                                marca,
                                modelo,
                                color,
                                serial,
                                monto,
                                cedula_empleado,
                                nombre_unidad
                            ) = fila

                            if BienNacional.objects.filter(serial=serial).exists():
                                raise Exception("Serial duplicado")

                            if BienNacional.objects.filter(nro_identificacion=nro_identificacion).exists():
                                raise Exception("ID duplicado")

                            empleado = Empleado.objects.get(cedula=cedula_empleado)
                            unidad = UnidadTrabajo.objects.get(nombre=nombre_unidad)

                            bien = BienNacional(
                                nro_identificacion=nro_identificacion,
                                subcuenta=subcuenta,
                                descripcion=descripcion,
                                marca=marca,
                                modelo=modelo,
                                color=color,
                                serial=serial,
                                monto=monto,
                                empleado_uso=empleado,
                                unidad_trabajo=unidad
                            )

                            bienes_crear.append(bien)

                        except Exception as e:
                            errores.append(f"Error en fila {fila}: {str(e)}")

                    BienNacional.objects.bulk_create(bienes_crear)
                    for bien in bienes_crear:
                        bien.save()

                messages.success(request, f"Carga completada. {len(bienes_crear)} registros insertados.")
                if errores:
                    messages.warning(request, f"Errores encontrados: {len(errores)}")

                return redirect('bien_list')

            except Exception as e:
                messages.error(request, f"Error general: {str(e)}")

    else:
        form = CargaMasivaForm()

    return render(request, "bienes/carga_masiva.html", {"form": form})


# ==========================
# Dashboard
# ==========================

class BienesDashboardView(TemplateView):
    template_name = 'bienes/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Estadísticas rápidas para las tarjetas
        context['total_bienes'] = BienNacional.objects.count()
        context['total_empleados'] = Empleado.objects.count()
        context['bienes_operativos'] = BienNacional.objects.filter(estado_bien='Buen Estado').count()
        return context
    



    

# ==========================
# estadisticas
# ==========================



class EstadisticasView(TemplateView):
    template_name = 'bienes/estadisticas.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. KPIs Generales
        context['total_bienes'] = BienNacional.objects.count()
        context['inversion_total'] = BienNacional.objects.aggregate(Sum('monto'))['monto__sum'] or 0
        
        # 2. Datos por Unidad de Trabajo
        unidades_data = BienNacional.objects.values('unidad_trabajo__nombre').annotate(total=Count('id'))
        context['labels_unidades'] = [item['unidad_trabajo__nombre'] for item in unidades_data]
        context['data_unidades'] = [item['total'] for item in unidades_data]

        # 3. CORRECCIÓN AQUÍ: Usamos 'estado_bien' en lugar de 'condicion'
        estado_data = BienNacional.objects.values('estado_bien').annotate(total=Count('id'))
        
        # Mapeamos los resultados para que se vean bien en el gráfico
        context['labels_estado'] = [item['estado_bien'] for item in estado_data]
        context['data_estado'] = [item['total'] for item in estado_data]

        return context
    
    
    
 # ==========================
# Vistas de detalle e historial
# ==========================   
class BienDetailView(DetailView):
    model = BienNacional
    template_name = 'bienes/bienes/detalle.html'
    context_object_name = 'bien'

class BienHistorialView(DetailView):
    model = BienNacional
    template_name = 'bienes/bienes/detalle_historial.html'
    context_object_name = 'bien'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # CORRECCIÓN: Usamos 'fecha' en lugar de 'fecha_movimiento'
        context['historial'] = self.object.movimientobien_set.all().order_by('-fecha')
        return context
    

    
 # ==========================
# vconsulta pública detallada
# ==========================   
class BienConsultaPublicaView(DetailView):
    model = BienNacional
    template_name = 'bienes/bienes/consulta_publica.html'
    context_object_name = 'bien'
    
    

 # ==========================
# crear nueva unidad de trabajo 
# ==========================   
class UnidadTrabajoCreateView(CreateView):
    model = UnidadTrabajo
    fields = ['nombre', 'parroquia', 'ciudad', 'direccion']
    template_name = 'bienes/bienes/unidad_form.html'
    success_url = reverse_lazy('bienes:bien_list') 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Registrar Unidad de Trabajo"
        return context

# Filtrado de parroquias para el formulario de unidad de trabajo (AJAX)
def load_parroquias(request):
    ciudad_id = request.GET.get('ciudad_id')
    
    if not ciudad_id:
        return JsonResponse([], safe=False)

    try:
        ciudad = Ciudad.objects.get(id=ciudad_id)
        
        parroquias = Parroquia.objects.filter(
            municipio__estado=ciudad.estado
        ).values('id', 'nombre').order_by('nombre')
        
        return JsonResponse(list(parroquias), safe=False)
        
    except Ciudad.DoesNotExist:
        return JsonResponse([], safe=False)



 # ==========================
# crear nueva ubicaciones geográficas
# ==========================   
class GestionGeograficaView(TemplateView):
    template_name = 'bienes/bienes/geografia_gestion.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Optimizamos para evitar consultas lentas
        context['regiones'] = Region.objects.all().order_by('nombre')
        context['estados'] = Estado.objects.select_related('region').all().order_by('nombre')
        context['municipios'] = Municipio.objects.select_related('estado').all().order_by('nombre')
        context['ciudades'] = Ciudad.objects.select_related('estado').all().order_by('nombre')
        context['parroquias'] = Parroquia.objects.select_related('municipio__estado').all().order_by('nombre')
        return context

# --- Mixin para simplificar las vistas de creación ---
class GeoCreateMixin:
    success_url = reverse_lazy('bienes:geografia_gestion')
    
    def form_valid(self, form):
        messages.success(self.request, f"{self.model.__name__} guardado correctamente.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Error al guardar. Verifique los datos.")
        return redirect('bienes:geografia_gestion')

# --- Vistas Finales ---

class RegionCreateView(GeoCreateMixin, CreateView):
    model = Region
    fields = ['nombre']

class EstadoCreateView(GeoCreateMixin, CreateView):
    model = Estado
    fields = ['nombre', 'region']

class MunicipioCreateView(GeoCreateMixin, CreateView):
    model = Municipio
    fields = ['nombre', 'estado']

class CiudadCreateView(GeoCreateMixin, CreateView):
    model = Ciudad
    fields = ['nombre', 'estado']

class ParroquiaCreateView(GeoCreateMixin, CreateView):
    model = Parroquia
    fields = ['nombre', 'municipio']
    
    

# Filtrado de estados, municipios y detalles para los formularios (AJAX)



# --- CARGA DE SELECTORES (CASCADA) ---

def ajax_load_estados(request):
    region_id = request.GET.get('region_id')
    if not region_id:
        return JsonResponse([], safe=False)
    estados = Estado.objects.filter(region_id=region_id).values('id', 'nombre').order_by('nombre')
    return JsonResponse(list(estados), safe=False)

def ajax_load_municipios(request):
    estado_id = request.GET.get('estado_id')
    if not estado_id:
        return JsonResponse([], safe=False)
    municipios = Municipio.objects.filter(estado_id=estado_id).values('id', 'nombre').order_by('nombre')
    return JsonResponse(list(municipios), safe=False)

def ajax_load_ciudades(request):
    estado_id = request.GET.get('estado_id')
    if not estado_id:
        return JsonResponse([], safe=False)
    ciudades = Ciudad.objects.filter(estado_id=estado_id).values('id', 'nombre').order_by('nombre')
    return JsonResponse(list(ciudades), safe=False)

def ajax_load_parroquias(request):
    municipio_id = request.GET.get('municipio_id')
    if not municipio_id:
        return JsonResponse([], safe=False)
    parroquias = Parroquia.objects.filter(municipio_id=municipio_id).values('id', 'nombre').order_by('nombre')
    return JsonResponse(list(parroquias), safe=False)

# --- RENDERIZADO DE TARJETAS EN EL EXPLORADOR ---

def ajax_load_detalles_finales(request):
    nivel = request.GET.get('nivel')
    id_ref = request.GET.get('id')
    resultados = []

    if not id_ref or id_ref == "":
        return JsonResponse([], safe=False)

    try:
        if nivel == 'region':
            # Al elegir Región -> Mostramos sus Estados
            objs = Estado.objects.filter(region_id=id_ref).select_related('region').order_by('nombre')
            for o in objs:
                resultados.append({'nombre': o.nombre, 'tipo': 'Estado', 'superior': o.region.nombre})
                
        elif nivel == 'estado':
            # Al elegir Estado -> Mostramos Municipios y Ciudades
            munis = Municipio.objects.filter(estado_id=id_ref).select_related('estado').order_by('nombre')
            ciudades = Ciudad.objects.filter(estado_id=id_ref).select_related('estado').order_by('nombre')
            for m in munis:
                resultados.append({'nombre': m.nombre, 'tipo': 'Municipio', 'superior': m.estado.nombre})
            for c in ciudades:
                resultados.append({'nombre': c.nombre, 'tipo': 'Ciudad', 'superior': c.estado.nombre})

        elif nivel == 'municipio':
            # Al elegir Municipio -> Mostramos sus Parroquias
            parroquias = Parroquia.objects.filter(municipio_id=id_ref).select_related('municipio').order_by('nombre')
            for p in parroquias:
                resultados.append({'nombre': p.nombre, 'tipo': 'Parroquia', 'superior': p.municipio.nombre})

        elif nivel == 'ciudad':
            # NUEVO: Al elegir una Ciudad específica -> Mostramos la tarjeta de esa ciudad
            c = Ciudad.objects.select_related('estado').get(id=id_ref)
            resultados.append({'nombre': c.nombre, 'tipo': 'Ciudad', 'superior': c.estado.nombre})

        elif nivel == 'parroquia':
            # NUEVO: Al elegir una Parroquia específica -> Mostramos la tarjeta de esa parroquia
            p = Parroquia.objects.select_related('municipio').get(id=id_ref)
            resultados.append({'nombre': p.nombre, 'tipo': 'Parroquia', 'superior': p.municipio.nombre})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse(resultados, safe=False)