from django.views.generic import *
from django.urls import reverse_lazy
from .models import *
from .forms import *
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
import csv
import openpyxl
from django.db import transaction
from django.contrib import messages
import uuid

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
    success_url = reverse_lazy('bienes:biene_list')

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

# ==========================
# vista para generar PDF
# ==========================
from django.http import FileResponse
from .utils import generar_etiqueta_pdf
import os
from django.conf import settings


def generar_etiqueta(request, pk):
    bien = get_object_or_404(BienNacional, pk=pk)

    ruta_relativa = generar_etiqueta_pdf(bien)
    ruta_completa = os.path.join(settings.MEDIA_ROOT, ruta_relativa)

    return FileResponse(open(ruta_completa, 'rb'), as_attachment=True)





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


class BienesDashboardView(TemplateView):
    template_name = 'bienes/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Estadísticas rápidas para las tarjetas
        context['total_bienes'] = BienNacional.objects.count()
        context['total_empleados'] = Empleado.objects.count()
        # Contamos cuántos bienes están en buen estado (ejemplo)
        context['bienes_operativos'] = BienNacional.objects.filter(estado_bien='Buen Estado').count()
        return context
    


class BienDetailView(DetailView):
    model = BienNacional
    template_name = 'bienes/bienes/detalle_historial.html'
    context_object_name = 'bien'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obtenemos los movimientos ordenados del más reciente al más antiguo
        context['historial'] = MovimientoBien.objects.filter(bien=self.object).order_of_recent()
        return context