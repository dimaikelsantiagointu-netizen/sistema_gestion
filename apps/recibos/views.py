import io
import os
import logging
import zipfile
import pytz
from datetime import datetime
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.db.models import Q, Sum, Count, Max
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.views.generic import ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required

# Importaciones locales de tu app
from .models import Recibo
from .forms import ReciboForm
from .constants import CATEGORY_CHOICES, ESTADO_CHOICES_MAP
from .utils import (
    importar_recibos_desde_excel, 
    generar_reporte_excel, 
    generar_pdf_reporte, 
    generar_pdf_recibo_unitario
)

# Logger configurado en settings para evitar mezclas con Auditoría
logger = logging.getLogger('apps.recibos')

# --- CONFIGURACIÓN DE RUTAS ---
try:
    HEADER_IMAGE = os.path.join(
        settings.BASE_DIR, 'apps', 'recibos', 'static', 'recibos', 'images', 'encabezado.png'
    )
except AttributeError:
    HEADER_IMAGE = os.path.join(os.path.dirname(__file__), '..', 'static', 'recibos', 'images', 'encabezado.png')

# --- VISTAS BASE ---

class PaginaBaseView(TemplateView):
    template_name = 'base.html'

# --- LÓGICA DE PDF Y ZIP (DESCARGAS) ---

@login_required
def generar_pdf_recibo(request, pk):
    """Genera el PDF de un recibo individual."""
    try:
        recibo = get_object_or_404(Recibo, pk=pk)
        return generar_pdf_recibo_unitario(recibo)
    except Exception as e:
        logger.error(f"Error al generar PDF unitario para PK={pk}: {e}")
        messages.error(request, f"Error al generar el PDF: {e}")
        return redirect('recibos:dashboard')

@login_required
def generar_zip_recibos(request):
    """Genera un archivo comprimido con múltiples recibos en PDF."""
    pks_str = request.GET.get('pks')
    if not pks_str:
        messages.error(request, "No se encontraron IDs de recibos para generar el ZIP.")
        return redirect('recibos:dashboard')

    try:
        pks = [int(pk) for pk in pks_str.split(',') if pk] 
        recibos = Recibo.objects.filter(pk__in=pks)
    except (ValueError, Exception) as e:
        logger.error(f"Error al procesar PKS para ZIP: {e}")
        messages.error(request, "Error en el formato de los IDs o al buscar registros.")
        return redirect('recibos:dashboard')

    zip_buffer = io.BytesIO()
    count_success = 0

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for recibo in recibos:
            try:
                pdf_response = generar_pdf_recibo_unitario(recibo)
                pdf_buffer_value = pdf_response.content

                num_recibo_zfill = str(recibo.numero_recibo).zfill(9) if recibo.numero_recibo else '0000'
                filename = f"Recibo_N_{num_recibo_zfill}_{recibo.rif_cedula_identidad}.pdf"

                zipf.writestr(filename, pdf_buffer_value)
                count_success += 1
            except Exception as e:
                logger.error(f"Error en PDF para ZIP (PK={recibo.pk}): {e}")

    if count_success == 0:
        messages.error(request, "No se pudo generar ningún PDF. El ZIP está vacío.")
        return redirect('recibos:dashboard')

    zip_buffer.seek(0)
    filename_zip = f"Recibos_Masivos_{timezone.now().strftime('%Y%m%d_%H%M%S')}.zip"
    
    response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{filename_zip}"'
    
    # Nota: El mensaje success se registrará en la siguiente carga de página del usuario
    messages.success(request, f"Se generó el ZIP con {count_success} recibo(s) exitosamente.")
    return response

# --- DASHBOARD Y FILTROS ---

class ReciboListView(LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin, ListView):
    model = Recibo
    template_name = 'recibos/dashboard.html'
    permission_required = 'users.ver_gestor_recibos'
    context_object_name = 'recibos'
    paginate_by = 20
    raise_exception = True
    
    def test_func(self):
        return self.request.user.is_superuser or (hasattr(self.request.user, 'rol') and self.request.user.rol in ['admin', 'user'])
    
    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')

        # --- Lógica de Anulación ---
        if action == 'anular':
            recibo_id = request.POST.get('recibo_id')
            if recibo_id:
                recibo = get_object_or_404(Recibo, pk=recibo_id)
                if not recibo.anulado:
                    recibo.anulado = True
                    recibo.fecha_anulacion = timezone.now() # Uso de timezone.now() corregido
                    recibo.save()
                    logger.info(f"Recibo N°{recibo.numero_recibo} ANULADO por {request.user}")
                    messages.success(request, f"El recibo N°{str(recibo.numero_recibo).zfill(9)} ha sido anulado.")
                else:
                    messages.warning(request, "Este recibo ya estaba anulado.")
            return redirect('recibos:dashboard')

        # --- Lógica de Limpiar Base de Datos (PROTEGIDA) ---
        elif action == 'clear_logs':
            if request.user.is_superuser:
                Recibo.objects.all().delete()
                logger.warning(f"VACIADO TOTAL de recibos ejecutado por {request.user}")
                messages.success(request, "Todos los recibos han sido eliminados.")
            else:
                messages.error(request, "No tienes permisos para vaciar la base de datos.")
            return redirect('recibos:dashboard')

        # --- Lógica de Carga de Excel ---
        elif action == 'upload':
            archivo_excel = request.FILES.get('archivo_recibo')
            if not archivo_excel:
                messages.error(request, "Por favor, sube un archivo Excel.")
            else:
                try:
                    success, message, pks = importar_recibos_desde_excel(archivo_excel, request.user)
                    if success:
                        messages.success(request, message)
                        if pks:
                            pks_str = ','.join(map(str, pks))
                            return redirect(f"{reverse('recibos:dashboard')}?download_pks={pks_str}")
                    else:
                        messages.error(request, f"Fallo en la carga: {message}")
                except Exception as e:
                    logger.error(f"Error importación Excel: {e}")
                    messages.error(request, f"Error al ejecutar la importación.")
            return redirect('recibos:dashboard')

        return redirect('recibos:dashboard')

    def get_queryset(self):
        queryset = Recibo.objects.filter(anulado=False).order_by('-fecha_creacion', '-numero_recibo')

        search_query = self.request.GET.get('q', '').strip()
        search_field = self.request.GET.get('field', 'todos')

        # Búsqueda textual integrada
        if search_query:
            if search_field != 'todos' and hasattr(Recibo, search_field):
                queryset = queryset.filter(**{f'{search_field}__icontains': search_query})
            else:
                q_objects = (
                    Q(nombre__icontains=search_query) |
                    Q(rif_cedula_identidad__icontains=search_query) |
                    Q(numero_recibo__icontains=search_query) |
                    Q(numero_transferencia__icontains=search_query) |
                    Q(estado__icontains=search_query)
                )
                queryset = queryset.filter(q_objects)

        # Filtros de Estado y Fechas
        estado = self.request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado__iexact=estado)

        f_inicio = self.request.GET.get('fecha_inicio')
        f_fin = self.request.GET.get('fecha_fin')
        if f_inicio:
            queryset = queryset.filter(fecha_creacion__date__gte=f_inicio)
        if f_fin:
            queryset = queryset.filter(fecha_creacion__date__lte=f_fin)

        # Filtros de Categoría (Checkboxes)
        category_filters = Q()
        for codigo, _ in CATEGORY_CHOICES:
            if self.request.GET.get(codigo) == 'on':
                category_filters |= Q(**{f'{codigo}': True})
        if category_filters:
            queryset = queryset.filter(category_filters)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estadísticas y parámetros de filtros
        context['recibos_hoy'] = Recibo.objects.filter(
            fecha_creacion__date=timezone.now().date(), 
            anulado=False
        ).count()

        context['estados_db'] = Recibo.objects.filter(anulado=False).exclude(
            estado__isnull=True
        ).exclude(estado='').values_list('estado', flat=True).distinct().order_by('estado')

        context['categorias_list'] = CATEGORY_CHOICES
        
        # Persistencia de filtros en el contexto
        context['current_estado'] = self.request.GET.get('estado')
        context['current_start_date'] = self.request.GET.get('fecha_inicio')
        context['current_end_date'] = self.request.GET.get('fecha_fin')

        # Limpieza para paginación (evita duplicar parámetros en la URL)
        request_get_copy = self.request.GET.copy()
        request_get_copy.pop('page', None)
        context['request_get'] = request_get_copy

        return context


# ==============================================================================
# 2. REPORTES Y EXPORTACIÓN MASIVA (Excel y PDF)
# ==============================================================================

@login_required
def generar_reporte_view(request):
    """
    Genera reportes en Excel o PDF aplicando filtros complejos de búsqueda, 
    fecha, categorías y estado.
    """
    # 1. Preparación del Queryset base (Solo activos)
    recibos_queryset = Recibo.objects.filter(anulado=False).order_by('-fecha_creacion', '-numero_recibo')

    filters = Q()
    filtros_aplicados = {}
    periodo_str = 'Todas las fechas'

    # 2. Aplicación de Filtros Dinámicos
    estado_seleccionado = request.GET.get('estado')
    if estado_seleccionado:
        filters &= Q(estado__iexact=estado_seleccionado)
    filtros_aplicados['estado'] = estado_seleccionado if estado_seleccionado else 'Todos los estados'

    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')

    try:
        if fecha_inicio_str:
            filters &= Q(fecha_creacion__date__gte=fecha_inicio_str)
            periodo_str = f"Desde: {fecha_inicio_str}"

        if fecha_fin_str:
            filters &= Q(fecha_creacion__date__lte=fecha_fin_str)
            if periodo_str == 'Todas las fechas':
                periodo_str = f"Hasta: {fecha_fin_str}"
            else:
                periodo_str = f"{periodo_str} Hasta: {fecha_fin_str}"
    except ValueError:
        pass
    
    filtros_aplicados['periodo'] = periodo_str

    # Manejo de categorías (Checkboxes on/off)
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

    # Manejo de búsqueda textual (Integridad de la Parte 1)
    search_query = request.GET.get('q')
    search_field = request.GET.get('field', 'todos')

    if search_query:
        query_norm = search_query.strip()
        if search_field != 'todos' and hasattr(Recibo, search_field):
            q_search = Q(**{f'{search_field}__icontains': query_norm})
        else:
            q_search = (
                Q(nombre__icontains=query_norm) |
                Q(rif_cedula_identidad__icontains=query_norm) |
                Q(numero_recibo__icontains=query_norm) |
                Q(numero_transferencia__icontains=query_norm) |
                Q(estado__icontains=query_norm)
            )
            try:
                recibo_id = int(query_norm)
                q_search |= Q(pk=recibo_id)
            except ValueError:
                pass
        filters &= q_search
        filtros_aplicados['busqueda'] = search_query
    else:
        filtros_aplicados['busqueda'] = 'Ninguna'

    recibos_filtrados = recibos_queryset.filter(filters)
    action = request.GET.get('action')
    
    # Ejecución de Exportación
    if action == 'excel':
        try:
            response = generar_reporte_excel(request.GET, recibos_filtrados, filtros_aplicados)
            logger.info(f"Reporte EXCEL generado por {request.user} - Total: {recibos_filtrados.count()}")
            return response
        except Exception as e:
            logger.error(f"Error reporte Excel: {e}")
            messages.error(request, f"Error al generar Excel: {e}")
            return redirect(f"{reverse('recibos:dashboard')}?{request.GET.urlencode()}")

    elif action == 'pdf':
        try:
            response = generar_pdf_reporte(recibos_filtrados, filtros_aplicados)
            logger.info(f"Reporte PDF generado por {request.user} - Total: {recibos_filtrados.count()}")
            return response
        except Exception as e:
            logger.error(f"Error reporte PDF: {e}")
            messages.error(request, f"Error al generar PDF: {e}")
            return redirect(f"{reverse('recibos:dashboard')}?{request.GET.urlencode()}")
            
    messages.error(request, "Acción no válida.")
    return redirect('recibos:dashboard')

# ==============================================================================
# 3. MODIFICACIÓN Y REGISTRO DE ANULADOS
# ==============================================================================

@login_required
def modificar_recibo(request, pk):
    recibo = get_object_or_404(Recibo, pk=pk)
    num_fill = str(recibo.numero_recibo).zfill(9) if recibo.numero_recibo else '0000'

    if recibo.anulado:
        messages.error(request, f"El recibo N°{num_fill} está ANULADO (Irreversible).")
        return redirect('recibos:recibos_anulados')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'anular':
            recibo.anulado = True
            recibo.fecha_anulacion = timezone.now()
            recibo.save()
            logger.warning(f"Recibo {num_fill} ANULADO por {request.user}")
            messages.warning(request, f"¡Recibo N°{num_fill} anulado exitosamente!")
            return redirect('recibos:dashboard')

        form = ReciboForm(request.POST, instance=recibo)
        if form.is_valid():
            form.save()
            logger.info(f"Recibo {num_fill} MODIFICADO por {request.user}")
            messages.success(request, f"¡Recibo N°{num_fill} actualizado!")
            return redirect('recibos:dashboard')
        else:
            messages.error(request, "Error en los datos. Verifique los campos.")
    else:
        form = ReciboForm(instance=recibo)

    return render(request, 'recibos/modificar_recibo.html', {'recibo': recibo, 'form': form})

@login_required
def recibos_anulados(request):
    """Listado de control para recibos anulados (Historial)"""
    queryset = Recibo.objects.filter(anulado=True).order_by('-fecha_anulacion')
    query = request.GET.get('q', '').strip()
    
    if query:
        queryset = queryset.filter(
            Q(numero_recibo__icontains=query) |
            Q(nombre__icontains=query) |
            Q(rif_cedula_identidad__icontains=query)
        )

    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'recibos/recibos_anulados.html', {
        'titulo': 'Historial de Anulados',
        'recibos': page_obj,
    })

# ==============================================================================
# 4. ESTADÍSTICAS Y RENDIMIENTO (BI)
# ==============================================================================

def es_administrador(user):
    return user.is_superuser or (hasattr(user, 'rol') and user.rol in ['admin', 'superadmin'])

@login_required
@user_passes_test(es_administrador, login_url='recibos:dashboard')
def estadisticas_view(request):
    # Parámetros y Tiempo Local (Venezuela)
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    estado_filtro = request.GET.get('estado')
    
    tz_vzl = pytz.timezone('America/Caracas')
    hoy = timezone.localtime(timezone.now(), tz_vzl).date()

    queryset = Recibo.objects.filter(anulado=False)

    # Aplicar Filtros a la Data Estadística
    if fecha_inicio:
        queryset = queryset.filter(fecha_creacion__date__gte=fecha_inicio)
    if fecha_fin:
        queryset = queryset.filter(fecha_creacion__date__lte=fecha_fin)
    if estado_filtro and estado_filtro != 'Todos':
        queryset = queryset.filter(estado__iexact=estado_filtro)

    # Cálculos Generales
    total_recibos = queryset.count()
    monto_total = queryset.aggregate(Sum('total_monto_bs'))['total_monto_bs__sum'] or 0
    
    # Sección "Hoy" (Independiente de filtros)
    recibos_hoy_total = Recibo.objects.filter(fecha_creacion__date=hoy, anulado=False).count()
    datos_estados_hoy = Recibo.objects.filter(
        fecha_creacion__date=hoy, anulado=False
    ).values('estado').annotate(total=Count('id')).order_by('-total')

    # Historial Diario (Gráfica de barras/líneas)
    datos_historial = queryset.annotate(
        dia_solo=TruncDay('fecha_creacion', tzinfo=tz_vzl)
    ).values('dia_solo').annotate(total=Count('id')).order_by('dia_solo')

    max_dia = max([d['total'] for d in datos_historial]) if datos_historial else 0
    historial_dias = []
    for item in datos_historial:
        if item['dia_solo']:
            porcentaje = (item['total'] / max_dia * 100) if max_dia > 0 else 0
            historial_dias.append({
                'fecha': item['dia_solo'].date(),
                'total': item['total'],
                'porcentaje': porcentaje
            })

    # Estadísticas por Categoría
    categorias_config = [
        ('categoria1', 'Título Tierra Urbana'), ('categoria2', 'Título + Vivienda'),
        ('categoria3', 'Municipal'), ('categoria4', 'Tierra Privada'),
        ('categoria5', 'Tierra INAVI'), ('categoria6', 'Excedentes Título'),
        ('categoria7', 'Excedentes INAVI'), ('categoria8', 'Estudio Técnico'),
        ('categoria9', 'Locales Comerciales'), ('categoria10', 'Arrendamiento Terrenos'),
    ]
    estadisticas_categorias = []
    for campo, nombre_real in categorias_config:
        count = queryset.filter(**{campo: True}).count()
        if count > 0:
            porcentaje_cat = (count / total_recibos * 100) if total_recibos > 0 else 0
            estadisticas_categorias.append({'nombre': nombre_real, 'total': count, 'porcentaje': porcentaje_cat})

    # Distribución Regional (Gráfica Global reincorporada)
    top_estados = queryset.values('estado').annotate(total=Count('id')).order_by('-total')[:10]

    # Ranking de Usuarios (Performance)
    ranking_raw = queryset.values('usuario').annotate(total=Count('id')).order_by('-total')
    ranking_usuarios = []
    for item in ranking_raw:
        if item['usuario']:
            try:
                user_obj = User.objects.get(pk=item['usuario'])
                ranking_usuarios.append({'usuario': user_obj, 'total': item['total']})
            except User.DoesNotExist:
                continue

    estados_disponibles = Recibo.objects.exclude(estado__isnull=True).exclude(estado='').values_list('estado', flat=True).distinct().order_by('estado')

    context = {
        'total_recibos': total_recibos,
        'recibos_hoy_total': recibos_hoy_total,
        'monto_total': monto_total,
        'categorias': estadisticas_categorias,
        'top_estados': top_estados,
        'datos_estados_hoy': datos_estados_hoy,
        'estados_db': estados_disponibles,
        'historial_dias': historial_dias,
        'ranking_usuarios': ranking_usuarios,
        'filtros': {'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin, 'estado': estado_filtro}
    }
    return render(request, 'recibos/estadisticas.html', context)

@login_required
@user_passes_test(es_administrador)
def rendimiento_usuarios(request):
    """Vista dedicada al rendimiento detallado de analistas"""
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    filtros = Q(anulado=False)
    if fecha_inicio and fecha_fin:
        filtros &= Q(fecha_creacion__date__range=[fecha_inicio, fecha_fin])
    
    ranking = Recibo.objects.filter(filtros).values('usuario').annotate(total=Count('id')).order_by('-total')
    
    ranking_data = []
    total_general = 0
    for item in ranking:
        if item['usuario']:
            try:
                user = User.objects.get(pk=item['usuario'])
                ranking_data.append({'usuario': user, 'total': item['total']})
                total_general += item['total']
            except User.DoesNotExist:
                continue
            
    return render(request, 'recibos/usuarios_performance.html', {
        'ranking_usuarios': ranking_data,
        'total_general_periodo': total_general,
    })