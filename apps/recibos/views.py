from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView # UpdateView si la usas
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse
from django.db.models import Q, Max 
from datetime import datetime

from .models import Recibo, MAPEO_CATEGORIAS
from .forms import (
    ExcelUploadForm, 
    ReporteFiltrosForm,
    ReciboModelForm 
)
from .utils import (
    generar_pdf_individual, 
    generar_reporte_excel_django, 
    obtener_recibos_filtrados,
    generar_reporte_pdf_django 
)
class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff

class ExcelUploadView(LoginRequiredMixin, AdminRequiredMixin, View):
    template_name = 'recibos/upload_excel.html'

    def get(self, request):
        form = ExcelUploadForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = ExcelUploadForm(request.POST, request.FILES)

        if form.is_valid():
            excel_file = request.FILES['excel_file']
            
            from .utils import procesar_excel_sync 
            
            procesar_excel_sync(excel_file.read(), request.user)
            
            return render(request, self.template_name, {
                'form': form, 
                'success_message': '✅ Archivo procesado con éxito. Verifique el listado de recibos.'
            })

        return render(request, self.template_name, {'form': form})

class ReciboListView(LoginRequiredMixin, ListView):
    model = Recibo
    template_name = 'recibos/dashboard.html'
    context_object_name = 'recibos'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')
        estado = self.request.GET.get('estado')
        anulado = self.request.GET.get('anulado')
        
        
        if query:
            queryset = queryset.filter(
                Q(nombre__icontains=query) |
                Q(numero_recibo__icontains=query) |
                Q(numero_transferencia__icontains=query) |
                Q(rif_cedula_identidad__icontains=query)
            )

        if estado and estado != 'Todos':
            queryset = queryset.filter(estado=estado)
            
        if anulado == 'True':
            queryset = queryset.filter(anulado=True)
        else:
            queryset = queryset.filter(anulado=False)

        return queryset.order_by('-fecha', '-numero_recibo')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estado_choices'] = Recibo.ESTADO_CHOICES
        context['current_query'] = self.request.GET.get('q', '')
        context['current_estado'] = self.request.GET.get('estado', 'Todos')
        context['current_anulado'] = self.request.GET.get('anulado', 'False')
        context['selected_categories'] = self.request.GET.getlist('categories')
        return context

class ReciboCreateView(LoginRequiredMixin, CreateView):
    model = Recibo
    form_class = ReciboModelForm 
    template_name = 'recibos/recibo_form.html' 
    success_url = reverse_lazy('recibos:recibo_list') 

    def form_valid(self, form):
        form.instance.usuario_creador = self.request.user.username 
        return super().form_valid(form)

class ReciboUpdateView(LoginRequiredMixin, View):
    template_name = 'recibos/recibo_form.html'

    def get(self, request, pk):
        recibo = get_object_or_404(Recibo, pk=pk)
        form = ReciboModelForm(instance=recibo)
        return render(request, self.template_name, {'form': form, 'recibo': recibo})

    def post(self, request, pk):
        recibo = get_object_or_404(Recibo, pk=pk)
        form = ReciboModelForm(request.POST, instance=recibo)
        
        if form.is_valid():
            recibo = form.save(commit=False)
            recibo.usuario_creador = request.user.username
            recibo.save()
            if request.POST.get('regenerar_pdf_confirm') == 'on':
                generar_pdf_individual(recibo)
            
            return redirect('recibos:recibo_list')
        
        return render(request, self.template_name, {'form': form, 'recibo': recibo})


class AnularReciboView(LoginRequiredMixin, View):
    def post(self, request, pk):
        recibo = get_object_or_404(Recibo, pk=pk)
        
        if not recibo.anulado:
            recibo.anulado = True
            recibo.fecha_anulacion = datetime.now()
            recibo.usuario_anulo = request.user.username
            recibo.save()
            return redirect('recibos:recibo_list')
        
        return HttpResponse("El recibo ya estaba anulado.", status=400)


class GenerarPdfView(LoginRequiredMixin, View):
    def get(self, request, pk):
        recibo = get_object_or_404(Recibo, pk=pk)
        
        response = generar_pdf_individual(recibo) 
        
        return response


class ReporteGeneracionView(LoginRequiredMixin, View):
    template_name = 'recibos/reporte_filtros.html'
    
    def get(self, request):
        form = ReporteFiltrosForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = ReporteFiltrosForm(request.POST)
        
        if form.is_valid():
            data = form.cleaned_data
            
            fecha_inicio = data['fecha_inicio']
            fecha_fin = data['fecha_fin']
            estado_filtro = self.request.GET.get('estado')
            
            categorias_filtro = [int(c) for c in data['categorias_filtro']]
        if estado_filtro == 'anulado':
            queryset = queryset.filter(anulado=True)
        elif estado_filtro == 'activo' or not estado_filtro: # Si es 'activo' o 'Todos' (estado vacío)
            queryset = queryset.filter(anulado=False)
            formato = request.POST.get('formato')
            
            queryset = obtener_recibos_filtrados(
                fecha_inicio, fecha_fin, estado_filtro, categorias_filtro
            )

            if not queryset.exists():
                return render(request, self.template_name, {
                    'form': form,
                    'error_message': '⚠️ No se encontraron recibos con los filtros seleccionados.'
                })
            
            if formato == 'excel':
                return generar_reporte_excel_django(
                    queryset, 
                    data, 
                    request.user.get_full_name() or request.user.username
                )
            elif formato == 'pdf':
                return generar_reporte_pdf_django(
                    queryset, 
                    data,
                    request.user.get_full_name() or request.user.username
                )
                
        return render(request, self.template_name, {'form': form})
    
    