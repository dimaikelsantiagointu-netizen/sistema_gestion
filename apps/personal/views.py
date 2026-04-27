from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView, ListView, DetailView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q, Count
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin 

from .models import Personal, DocumentoPersonal
from .forms import PersonalForm
from apps.territorio.models import Estado, UnidadAdscrita
import logging

logger_personal = logging.getLogger('CH_PERSONAL')

# ==============================================================================
# 1. GESTIÓN DE PERSONAL (CRUD TRABAJADORES)
# ==============================================================================

class PersonalCreateView(LoginRequiredMixin, CreateView):
    model = Personal
    form_class = PersonalForm
    template_name = 'personal/personal_form.html'
    success_url = reverse_lazy('personal:lista')

    def form_valid(self, form):
        nombre = form.cleaned_data.get('nombres')
        cedula = form.cleaned_data.get('cedula')
        response = super().form_valid(form)
        messages.success(self.request, f"TRABAJADOR {nombre} REGISTRADO EXITOSAMENTE.")
        logger_personal.info(f"CREATE | TRABAJADOR: {nombre} | CNI: {cedula} | BY: {self.request.user}")
        return response

class PersonalListView(LoginRequiredMixin, ListView):
    model = Personal
    template_name = 'personal/personal_list.html'
    context_object_name = 'personal_list'
    paginate_by = 15

    def get_queryset(self):
        queryset = Personal.objects.select_related('unidad_adscrita', 'estado').all()
        unidad_id = self.request.GET.get('unidad')
        estado_id = self.request.GET.get('estado_f')
        busqueda = self.request.GET.get('q')

        if unidad_id:
            queryset = queryset.filter(unidad_adscrita_id=unidad_id)
        if estado_id:
            queryset = queryset.filter(estado_id=estado_id)
        if busqueda:
            queryset = queryset.filter(
                Q(cedula__icontains=busqueda) |
                Q(nombres__icontains=busqueda) |
                Q(apellidos__icontains=busqueda)
            )
        return queryset.order_by('-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unidades'] = UnidadAdscrita.objects.all()
        context['estados'] = Estado.objects.all()
        context['unidad_selected'] = self.request.GET.get('unidad', '')
        context['estado_selected'] = self.request.GET.get('estado_f', '')
        context['q_value'] = self.request.GET.get('q', '')
        return context

class PersonalUpdateView(LoginRequiredMixin, UpdateView):
    model = Personal
    form_class = PersonalForm
    template_name = 'personal/personal_form.html'
    success_url = reverse_lazy('personal:lista')

    def form_valid(self, form):
        nombre = form.cleaned_data.get('nombres')
        response = super().form_valid(form)
        messages.info(self.request, f"DATOS DE {nombre} ACTUALIZADOS CORRECTAMENTE.")
        logger_personal.info(f"UPDATE | TRABAJADOR_ID: {self.object.id} | BY: {self.request.user}")
        return response

class PersonalDetailView(LoginRequiredMixin, DetailView):
    model = Personal
    template_name = 'personal/personal_detail.html'
    context_object_name = 'trabajador'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['documentos'] = self.object.expediente_personal.all().order_by('-fecha_subida')
        context['categorias'] = [
            ('ID', 'Documento de Identidad'),
            ('CV', 'Síntesis Curricular (CV)'),
            ('ACAD', 'Títulos Académicos y Certificaciones'),
            ('CONT', 'Actas de Nombramiento o Contratos'),
            ('OTRO', 'Otros Soportes'),
        ]
        return context

# ==============================================================================
# 3. GESTIÓN DE ARCHIVOS (SUBIDA Y ELIMINACIÓN)
# ==============================================================================

@login_required
def subir_archivo_personal(request, pk):
    trabajador = get_object_or_404(Personal, pk=pk)
    if request.method == 'POST':
        archivo = request.FILES.get('archivo')
        categoria = request.POST.get('categoria')
        nombre_personalizado = request.POST.get('nombre_documento')

        if archivo:
            if archivo.size > 10 * 1024 * 1024:
                messages.error(request, "EL ARCHIVO EXCEDE EL LÍMITE DE 10MB.")
                return redirect('personal:detalle', pk=pk)
            
            try:
                doc = DocumentoPersonal.objects.create(
                    personal=trabajador,
                    archivo=archivo,
                    categoria=categoria,
                    nombre_documento=nombre_personalizado if nombre_personalizado else archivo.name
                )
                messages.success(request, f"DOCUMENTO VINCULADO: {doc.nombre_documento}")
                logger_personal.info(f"FILE_UPLOAD | DOC: {doc.nombre_documento} | TRABAJADOR: {trabajador.cedula}")
            except Exception as e:
                logger_personal.error(f"FILE_UPLOAD_ERROR: {str(e)}")
                messages.error(request, f"ERROR AL GUARDAR: {str(e)}")
        else:
            messages.error(request, "NO SE DETECTÓ NINGÚN ARCHIVO.")
    return redirect('personal:detalle', pk=pk)

@login_required
def eliminar_documento_personal(request, doc_id):
    documento = get_object_or_404(DocumentoPersonal, id=doc_id)
    persona_id = documento.personal.id
    nombre = documento.nombre_documento
    try:
        documento.delete()
        messages.warning(request, f"DOCUMENTO ELIMINADO: {nombre}")
        logger_personal.info(f"FILE_DELETE | DOC: {nombre} | BY: {request.user}")
    except Exception as e:
        logger_personal.error(f"FILE_DELETE_ERROR: {str(e)}")
        messages.error(request, "ERROR AL ELIMINAR EL DOCUMENTO.")
    return redirect('personal:detalle', pk=persona_id)