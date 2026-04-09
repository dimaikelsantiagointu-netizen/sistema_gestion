from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView, ListView, DetailView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q, Count
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin 

from .models import Personal, DocumentoPersonal, UnidadAdscrita 
from .forms import PersonalForm, UnidadAdscritaForm
from apps.territorio.models import Estado

# ==============================================================================
# 1. GESTIÓN DE PERSONAL (CRUD TRABAJADORES)
# ==============================================================================

class PersonalCreateView(LoginRequiredMixin, CreateView):
    model = Personal
    form_class = PersonalForm
    template_name = 'personal/personal_form.html'
    success_url = reverse_lazy('personal:lista')

    def form_valid(self, form):
        messages.success(self.request, f"TRABAJADOR {form.cleaned_data['nombres']} REGISTRADO EXITOSAMENTE.")
        return super().form_valid(form)

class PersonalListView(LoginRequiredMixin, ListView):
    model = Personal
    template_name = 'personal/personal_list.html'
    context_object_name = 'personal_list' # Asegúrate que coincida con tu template
    paginate_by = 15

    def get_queryset(self):
        # Usamos select_related para optimizar consultas de claves foráneas
        queryset = Personal.objects.select_related('unidad_adscrita', 'estado').all()
        
        # Capturamos los parámetros GET (Deben coincidir con el 'name' en el HTML)
        unidad_id = self.request.GET.get('unidad')
        estado_id = self.request.GET.get('estado_f') # En tu HTML pusiste 'estado_f'
        busqueda = self.request.GET.get('q')

        # Aplicamos los filtros si existen y no están vacíos
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
        # Datos para llenar los selects
        context['unidades'] = UnidadAdscrita.objects.all()
        context['estados'] = Estado.objects.all()
        
        # Importante: devolvemos los valores para que el template sepa qué marcar como 'selected'
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
        messages.info(self.request, f"DATOS DE {form.cleaned_data['nombres']} ACTUALIZADOS CORRECTAMENTE.")
        return super().form_valid(form)

class PersonalDetailView(LoginRequiredMixin, DetailView):
    model = Personal
    template_name = 'personal/personal_detail.html'
    context_object_name = 'trabajador'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Traemos los documentos asociados
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
# 2. SUBMÓDULO DE UNIDADES ADSCRITAS
# ==============================================================================

class UnidadListView(LoginRequiredMixin, ListView):
    model = UnidadAdscrita
    template_name = 'personal/unidades_list.html'
    context_object_name = 'unidades'

    def get_queryset(self):
        # Usamos el related_name definido en tu modelo para el count
        return UnidadAdscrita.objects.annotate(
            total_trabajadores=Count('personal_asignado')
        ).order_by('nombre')

class UnidadCreateView(LoginRequiredMixin, CreateView):
    model = UnidadAdscrita
    form_class = UnidadAdscritaForm
    template_name = 'personal/unidad_form.html'
    success_url = reverse_lazy('personal:unidades_lista')

    def form_valid(self, form):
        messages.success(self.request, "NUEVA UNIDAD REGISTRADA.")
        return super().form_valid(form)

class UnidadUpdateView(LoginRequiredMixin, UpdateView):
    model = UnidadAdscrita
    form_class = UnidadAdscritaForm
    template_name = 'personal/unidad_form.html'
    success_url = reverse_lazy('personal:unidades_lista')

    def form_valid(self, form):
        messages.info(self.request, "UNIDAD ACTUALIZADA CORRECTAMENTE.")
        return super().form_valid(form)

@login_required
def eliminar_unidad(request, pk):
    unidad = get_object_or_404(UnidadAdscrita, pk=pk)
    try:
        nombre = unidad.nombre
        unidad.delete()
        messages.warning(request, f"UNIDAD {nombre} ELIMINADA.")
    except Exception:
        messages.error(request, "NO SE PUEDE ELIMINAR: Esta unidad tiene personal asociado.")
    return redirect('personal:unidades_lista')

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
            try:
                DocumentoPersonal.objects.create(
                    personal=trabajador,
                    archivo=archivo,
                    categoria=categoria,
                    nombre_documento=nombre_personalizado if nombre_personalizado else archivo.name
                )
                messages.success(request, f"DOCUMENTO VINCULADO: {archivo.name}")
            except Exception as e:
                messages.error(request, f"ERROR AL GUARDAR: {str(e)}")
        else:
            messages.error(request, "NO SE DETECTÓ NINGÚN ARCHIVO.")
    return redirect('personal:detalle', pk=pk)

@login_required
def eliminar_documento_personal(request, doc_id):
    documento = get_object_or_404(DocumentoPersonal, id=doc_id)
    persona_id = documento.personal.id
    nombre = documento.nombre_documento
    documento.delete()
    messages.warning(request, f"DOCUMENTO ELIMINADO: {nombre}")
    return redirect('personal:detalle', pk=persona_id)