from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView, ListView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.decorators import login_required
# IMPORTANTE: Importamos el mixin para las clases
from django.contrib.auth.mixins import LoginRequiredMixin 

from .models import Personal, DocumentoPersonal
from .forms import PersonalForm

# ==============================================================================
# 1. REGISTRO DE PERSONAL (PROTEGIDO)
# ==============================================================================
class PersonalCreateView(LoginRequiredMixin, CreateView):
    model = Personal
    form_class = PersonalForm
    template_name = 'personal/personal_form.html'
    success_url = reverse_lazy('personal:lista')

    def form_valid(self, form):
        messages.success(self.request, f"TRABAJADOR {form.cleaned_data['nombres']} REGISTRADO EXITOSAMENTE.")
        return super().form_valid(form)

# ==============================================================================
# 2. LISTADO Y FILTROS INTELIGENTES (PROTEGIDO)
# ==============================================================================
class PersonalListView(LoginRequiredMixin, ListView):
    model = Personal
    template_name = 'personal/personal_list.html'
    context_object_name = 'personal_list'
    ordering = ['apellidos']

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q')
        
        # Mantenemos tu lógica de búsqueda: Solo filtrar si hay parámetros
        if q:
            queryset = queryset.filter(
                Q(cedula__icontains=q) | 
                Q(apellidos__icontains=q) |
                Q(nombres__icontains=q)
            )
            
        unidad = self.request.GET.get('unidad')
        if unidad:
            queryset = queryset.filter(unidad_adscrita=unidad)
            
        estatus = self.request.GET.get('estatus')
        if estatus:
            queryset = queryset.filter(activo=(estatus == 'activo'))
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unidades'] = Personal.objects.values_list('unidad_adscrita', flat=True).distinct()
        return context

# ==============================================================================
# 3. EXPEDIENTE DIGITAL (PROTEGIDO)
# ==============================================================================
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
# 4. GESTIÓN DE ARCHIVOS (PROTEGIDO POR DECORADORES)
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