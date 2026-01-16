from urllib import request
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.db.models import Q, Sum 
from django.contrib import messages
from .models import Recibo
import io
import os
import logging
from django.urls import reverse
from .utils import importar_recibos_desde_excel, generar_reporte_excel, generar_pdf_reporte, generar_pdf_recibo_unitario
from django.conf import settings
from django.views.generic import ListView, TemplateView
from .forms import ReciboForm
from .constants import CATEGORY_CHOICES, ESTADO_CHOICES_MAP
import zipfile
from django.utils import timezone
from datetime import datetime
import pytz 
from django.core.paginator import Paginator
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin
from django.views.generic import ListView
from django.contrib.auth.decorators import login_required
logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN DE RUTAS Y CONSTANTES (Mantener por si otras funciones lo usan) ---
try:
    HEADER_IMAGE = os.path.join(
        settings.BASE_DIR,
        'apps',
        'recibos',
        'static',
        'recibos',
        'images',
        'encabezado.png'
    )
except AttributeError:
    # Fallback si settings.BASE_DIR no está definido
    HEADER_IMAGE = os.path.join(os.path.dirname(__file__), '..', 'static', 'recibos', 'images', 'encabezado.png')

# --- CLASE BASE Y ELIMINACIÓN DE FUNCIONES REDUNDANTES ---

class PaginaBaseView( TemplateView):
    template_name = 'base.html'

# VISTAS DE DESCARGA Y LÓGICA DE PDF/ZIP

def generar_pdf_recibo(request, pk):

    try:
        recibo = get_object_or_404(Recibo, pk=pk)
        return generar_pdf_recibo_unitario(recibo)
    except Exception as e:
        logger.error(f"Error al generar PDF unitario para PK={pk}: {e}")
        messages.error(request, f"Error al generar el PDF: {e}")
        return redirect(reverse('recibos:dashboard')) 

def generar_zip_recibos(request):

    pks_str = request.GET.get('pks')
    if not pks_str:
        messages.error(request, "No se encontraron IDs de recibos para generar el ZIP.")
        return redirect(reverse('recibos:dashboard'))

    try:
        pks = [int(pk) for pk in pks_str.split(',') if pk] 
        recibos = Recibo.objects.filter(pk__in=pks)
    except ValueError:
        messages.error(request, "Error en el formato de los IDs de recibos.")
        return redirect(reverse('recibos:dashboard'))
    except Exception as e:
        messages.error(request, f"Error al buscar recibos: {e}")
        return redirect(reverse('recibos:dashboard'))

    zip_buffer = io.BytesIO()
    count_success = 0

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for recibo in recibos:
            try:
                pdf_response = generar_pdf_recibo_unitario(recibo)
                pdf_buffer_value = pdf_response.content

                num_recibo_zfill = str(recibo.numero_recibo).zfill(4) if recibo.numero_recibo else '0000'
                filename = f"Recibo_N_{num_recibo_zfill}_{recibo.rif_cedula_identidad}.pdf"

                zipf.writestr(filename, pdf_buffer_value)
                count_success += 1
            except Exception as e:
                logger.error(f"Error al generar el PDF para el recibo PK={recibo.pk}: {e}")

    zip_buffer.seek(0)

    if count_success == 0:
        messages.error(request, "No se pudo generar ningún PDF. El ZIP está vacío.")
        return redirect(reverse('recibos:dashboard'))

    filename_zip = f"Recibos_Masivos_{timezone.now().strftime('%Y%m%d_%H%M%S')}.zip"
    response = HttpResponse(
        zip_buffer.getvalue(),
        content_type='application/zip'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename_zip}"'
    
    messages.success(request, f"Se generó el ZIP con {count_success} recibo(s) exitosamente.")

    return response


# DASHBOARD Y FILTROS (ReciboListView)

class ReciboListView(LoginRequiredMixin, UserPassesTestMixin,PermissionRequiredMixin, ListView):
    model = Recibo
    template_name = 'recibos/dashboard.html'
    permission_required = 'users.ver_gestor_recibos'
    context_object_name = 'recibos'
    paginate_by = 20
    raise_exception = True
    
    def test_func(self):
        return self.request.user.rol in ['admin', 'user'] or self.request.user.is_superuser
    
    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        
        current_timezone = pytz.timezone(settings.TIME_ZONE) if hasattr(settings, 'TIME_ZONE') else timezone.get_current_timezone()

        if action == 'anular':
            recibo_id = request.POST.get('recibo_id')
            if recibo_id:
                recibo = get_object_or_404(Recibo, pk=recibo_id)
                num_recibo_zfill = str(recibo.numero_recibo).zfill(4) if recibo.numero_recibo else '0000'

                if not recibo.anulado:
                    recibo.anulado = True
                    recibo.fecha_anulacion = datetime.now(current_timezone)
                    recibo.save()
                    messages.success(request, f"El recibo N°{num_recibo_zfill} ha sido ANULADO correctamente.")
                else:
                    messages.warning(request, "Este recibo ya estaba anulado.")
            else:
                messages.error(request, "No se proporcionó el ID del recibo a anular.")
            return redirect(reverse('recibos:dashboard'))

        elif action == 'clear_logs':
            Recibo.objects.all().delete()
            messages.success(request, "Todos los recibos han sido eliminados de la base de datos.")
            return redirect(reverse('recibos:dashboard'))

        elif action == 'upload':
            archivo_excel = request.FILES.get('archivo_recibo')
            if not archivo_excel:
                messages.error(request, "Por favor, sube un archivo Excel.")
            else:
                try:
                    success, message, pks = importar_recibos_desde_excel(archivo_excel, request.user)
                    if success and pks and isinstance(pks, list):
                        messages.success(request, message)

                        if len(pks) == 1:
                            return redirect(reverse('recibos:generar_pdf_recibo', kwargs={'pk': pks[0]}))
                        else:
                            pks_str = ','.join(map(str, pks))
                            return redirect(reverse('recibos:generar_zip_recibos') + f'?pks={pks_str}')

                    elif success:
                        messages.warning(request, message)
                    else:
                        messages.error(request, f"Fallo en la carga de Excel: {message}")

                except Exception as e:
                    logger.error(f"Error al ejecutar la importación de Excel: {e}")
                    messages.error(request, f"Error interno en la lógica de importación: {e}")

            return redirect(reverse('recibos:dashboard'))

        return redirect(reverse('recibos:dashboard'))


    def get_queryset(self):
        queryset = Recibo.objects.filter(anulado=False).order_by('-fecha', '-numero_recibo')

        search_query = self.request.GET.get('q')
        search_field = self.request.GET.get('field', '')

        # --- Lógica de Búsqueda 
        if search_query:
            query_normalizado = search_query.strip()
            
            if search_field and search_field != 'todos' and hasattr(Recibo, search_field):
                try:
                    filtro = {f'{search_field}__icontains': query_normalizado}
                    queryset = queryset.filter(**filtro)
                except Exception as e:
                    logger.error(f"Error al filtrar por campo dinámico {search_field}: {e}")
            else:
                q_objects = (
                    Q(nombre__icontains=query_normalizado) |
                    Q(rif_cedula_identidad__icontains=query_normalizado) |
                    Q(numero_recibo__iexact=query_normalizado) |
                    Q(numero_transferencia__icontains=query_normalizado) |
                    Q(estado__icontains=query_normalizado)
                )

                try:
                    recibo_id = int(query_normalizado)
                    q_objects |= Q(pk=recibo_id)
                except ValueError:
                    pass

                queryset = queryset.filter(q_objects)

        # --- Filtros de Estado y Fechas  ---
        estado_seleccionado = self.request.GET.get('estado')
        if estado_seleccionado and estado_seleccionado != "":
            queryset = queryset.filter(estado__iexact=estado_seleccionado)

        fecha_inicio_str = self.request.GET.get('fecha_inicio')
        fecha_fin_str = self.request.GET.get('fecha_fin')

        try:
            if fecha_inicio_str:
                queryset = queryset.filter(fecha__gte=fecha_inicio_str)
            if fecha_fin_str:
                queryset = queryset.filter(fecha__lte=fecha_fin_str)
        except ValueError:
            pass

        # --- Filtros de Categoría  ---
        category_filters = Q()
        for codigo, _ in CATEGORY_CHOICES:
            if self.request.GET.get(codigo) == 'on':
                category_filters |= Q(**{f'{codigo}': True})

        if category_filters:
            queryset = queryset.filter(category_filters)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Consulta eficiente de estados únicos.
        context['estados_db'] = Recibo.objects.filter(anulado=False).exclude(
            estado__isnull=True
        ).exclude(
            estado__exact=''
        ).values_list(
            'estado', flat=True
        ).distinct().order_by('estado')

        context['categorias_list'] = CATEGORY_CHOICES
        context['current_estado'] = self.request.GET.get('estado')
        context['current_start_date'] = self.request.GET.get('fecha_inicio')
        context['current_end_date'] = self.request.GET.get('fecha_fin')

        # Manejo de parámetros GET para la paginación 
        request_get_copy = self.request.GET.copy()
        if 'page' in request_get_copy:
            del request_get_copy['page']

        if 'q' in request_get_copy and not request_get_copy['q']:
            del request_get_copy['q']
        if 'field' in request_get_copy and not request_get_copy['field']:
            del request_get_copy['field']

        context['request_get'] = request_get_copy

        return context


# VISTAS DE REPORTE (Excel y PDF Masivo)

def generar_reporte_view(request):

    
    # 1. Preparación del Queryset base
    recibos_queryset = Recibo.objects.filter(anulado=False).order_by('-fecha', '-numero_recibo')

    filters = Q()
    filtros_aplicados = {}
    periodo_str = 'Todas las fechas'

    # 2. Aplicación de Filtros 
    estado_seleccionado = request.GET.get('estado')
    if estado_seleccionado and estado_seleccionado != "":
        filters &= Q(estado__iexact=estado_seleccionado)
    filtros_aplicados['estado'] = estado_seleccionado if estado_seleccionado else 'Todos los estados'

    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')

    # Manejo de período
    try:
        if fecha_inicio_str:
            filters &= Q(fecha__gte=fecha_inicio_str)
            periodo_str = f"Desde: {fecha_inicio_str}"

        if fecha_fin_str:
            filters &= Q(fecha__lte=fecha_fin_str)
            if periodo_str == 'Todas las fechas':
                periodo_str = f"Hasta: {fecha_fin_str}"
            else:
                periodo_str = f"{periodo_str} Hasta: {fecha_fin_str}"
    except ValueError:
        pass
    filtros_aplicados['periodo'] = periodo_str.replace('Todas las fechas Hasta: None', 'Todas las fechas')

    # Manejo de categorías
    selected_categories_names = []
    category_filters = Q()
    for codigo, nombre_display in CATEGORY_CHOICES:
        if request.GET.get(codigo) == 'on':
            category_filters |= Q(**{f'{codigo}': True})
            selected_categories_names.append(nombre_display)

    if category_filters:
        filters &= category_filters
        filtros_aplicados['categorias'] = ', '.join(selected_categories_names)
    else:
        filtros_aplicados['categorias'] = 'Todas las categorías'

    # Manejo de búsqueda
    search_query = request.GET.get('q')
    search_field = request.GET.get('field', '')

    if search_query:
        query_normalizado = search_query.strip()
        q_search = Q()
        if search_field and search_field != 'todos' and hasattr(Recibo, search_field):
            q_search = Q(**{f'{search_field}__icontains': query_normalizado})
        else:
            q_search = (
                Q(nombre__icontains=query_normalizado) |
                Q(rif_cedula_identidad__icontains=query_normalizado) |
                Q(numero_recibo__iexact=query_normalizado) |
                Q(numero_transferencia__icontains=query_normalizado) |
                Q(estado__icontains=query_normalizado)
            )
            try:
                recibo_id = int(query_normalizado)
                q_search |= Q(pk=recibo_id)
            except ValueError:
                pass
        filters &= q_search
        filtros_aplicados['busqueda'] = search_query
    else:
        filtros_aplicados['busqueda'] = 'Ninguna'

    # Filtrar el queryset final
    recibos_filtrados = recibos_queryset.filter(filters)
    
    # Manejo de la acción (excel o pdf)
    action = request.GET.get('action')
    
    if action == 'excel':
        try:
            response = generar_reporte_excel(request.GET, recibos_filtrados, filtros_aplicados)
            messages.success(request, f"El reporte Excel ({len(recibos_filtrados)} recibos) ha sido generado con éxito.")
            return response
            
        except Exception as e:
            logger.error(f"Error al generar el reporte Excel: {e}")
            messages.error(request, f"Error al generar el reporte Excel. Detalles: {e}")
            return redirect(reverse('recibos:dashboard') + '?' + request.GET.urlencode())

    elif action == 'pdf':
        try:
            response = generar_pdf_reporte(recibos_filtrados, filtros_aplicados)
            messages.success(request, f"El reporte PDF ({len(recibos_filtrados)} recibos) ha sido generado con éxito.")
            return response
            
        except Exception as e:
            logger.error(f"Error al generar el reporte PDF: {e}")
            messages.error(request, f"Error al generar el reporte PDF. Consulte la consola del servidor: {e}")
            return redirect(reverse('recibos:dashboard') + '?' + request.GET.urlencode())
            
    else:
        messages.error(request, "Acción de reporte no válida.")
        return redirect(reverse('recibos:dashboard') + '?' + request.GET.urlencode())


# VISTAS DE MODIFICACIÓN Y ANULACIÓN
@login_required
def modificar_recibo(request, pk):

    recibo = get_object_or_404(Recibo, pk=pk)

    num_recibo_zfill = str(recibo.numero_recibo).zfill(4) if recibo.numero_recibo else '0000'
    
    current_timezone = pytz.timezone(settings.TIME_ZONE) if hasattr(settings, 'TIME_ZONE') else timezone.get_current_timezone()


    if recibo.anulado:
        messages.error(request, f"El recibo N°{num_recibo_zfill} se encuentra ANULADO y es irreversible. No se pueden realizar cambios.")
        return redirect(reverse('recibos:recibos_anulados'))

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'anular':
            
            recibo.anulado = True
            recibo.fecha_anulacion = datetime.now(current_timezone)
            recibo.save()
            messages.warning(request, f"¡Recibo N°{num_recibo_zfill} ha sido ANULADO exitosamente! (Acción irreversible)")

            return redirect(reverse('recibos:dashboard'))

        else:
            form = ReciboForm(request.POST, instance=recibo)

            if form.is_valid():
                form.save()
                messages.success(request, f"¡Recibo N°{num_recibo_zfill} modificado exitosamente!")
                return redirect(reverse('recibos:dashboard'))
            else:
                messages.error(request, "Error al guardar los cambios. Por favor, revisa los campos.")


    else:
        form = ReciboForm(instance=recibo)

    context = {
        'recibo': recibo,
        'form': form,
    }

    return render(request, 'recibos/modificar_recibo.html', context)

@login_required
def recibos_anulados(request):

    # 1. Obtener todos los recibos anulados
    queryset = Recibo.objects.filter(anulado=True).order_by('-fecha_anulacion')

    # 2. Manejar la Búsqueda (Filtro por q)
    query = request.GET.get('q')
    if query:
        query_normalizado = query.strip()
        queryset = queryset.filter(
            Q(numero_recibo__icontains=query_normalizado) |
            Q(nombre__icontains=query_normalizado) |
            Q(rif_cedula_identidad__icontains=query_normalizado)
        )

    # 3. Manejar la Paginación (20 ítems por página)
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    recibos_page = paginator.get_page(page_number)

    context = {
        'titulo': 'Recibos Anulados',
        'recibos': recibos_page,
    }
    return render(request, 'recibos/recibos_anulados.html', context)