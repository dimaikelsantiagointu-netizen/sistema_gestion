from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, FileResponse
from django.db.models import Q, Sum
from django.contrib import messages
from .models import Recibo
import io
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph
from decimal import Decimal
import logging
from django.urls import reverse
# 🛑 IMPORTACIÓN CORREGIDA: Asegúrate de importar la utilidad de recibo unitario
from .utils import importar_recibos_desde_excel, generar_reporte_excel, generar_pdf_reporte, generar_pdf_recibo_unitario 
from django.conf import settings
from django.views.generic import ListView, TemplateView
from .forms import ReciboForm
from .constants import CATEGORY_CHOICES_MAP, CATEGORY_CHOICES, ESTADO_CHOICES_MAP
import zipfile
from django.utils import timezone
import pandas as pd
from reportlab.lib.styles import getSampleStyleSheet

logger = logging.getLogger(__name__)


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
    HEADER_IMAGE = os.path.join(os.path.dirname(__file__), '..', 'static', 'recibos', 'images', 'encabezado.png')


class PaginaBaseView(TemplateView):
    template_name = 'base.html'

# ❌ LÓGICA DE GENERACIÓN DE PDF ELIMINADA:
# Se ha movido a .utils.generar_pdf_recibo_unitario para centralizar.
# Las funciones de dibujo y formateo auxiliar (draw_text_line, format_currency, draw_centered_text_right)
# deben ser revisadas si se usan en generate_receipt_pdf. Si no se usan en otro lugar, también deben eliminarse.
# Si se usan en utils.py, se deben mover a utils.py o mantenerse aquí si utils.py las importa desde aquí.
# Por simplicidad, he dejado las funciones auxiliares aquí, asumiendo que generate_receipt_pdf fue eliminada.

def format_currency(amount):
    """Formatea el monto como moneda (ej: 1.234,56)."""
    try:
        amount_decimal = Decimal(amount)
        formatted = "{:,.2f}".format(amount_decimal)
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00"

def draw_text_line(canvas_obj, text, x_start, y_start, font_name="Helvetica", font_size=10, is_bold=False):
    """Dibuja una línea de texto y ajusta la posición Y."""
    font = font_name + "-Bold" if is_bold else font_name
    canvas_obj.setFont(font, font_size)
    canvas_obj.drawString(x_start, y_start, str(text))
    return y_start - 15

def draw_centered_text_right(canvas_obj, y_pos, text, x_start, width, font_name="Helvetica", font_size=10, is_bold=False):
    """Centra el texto dentro de un ancho específico."""
    font = font_name + "-Bold" if is_bold else font_name
    canvas_obj.setFont(font, font_size)
    text_width = canvas_obj.stringWidth(text, font, font_size)
    x = x_start + (width - text_width) / 2
    canvas_obj.drawString(x, y_pos, text.upper())

# ❌ FUNCIÓN generate_receipt_pdf ELIMINADA

# 🛑 FUNCIÓN CORREGIDA
def generar_pdf_recibo(request, pk):
    """
    Genera el PDF de un recibo específico y retorna el HttpResponse para
    la descarga directa (Usada por el botón del dashboard).
    """
    try:
        recibo = get_object_or_404(Recibo, pk=pk)
        
        # ✅ CORRECCIÓN CLAVE: Llama a la utilidad de descarga y retorna su respuesta.
        return generar_pdf_recibo_unitario(recibo)

    except Exception as e:
        logger.error(f"Error al generar PDF unitario para PK={pk}: {e}")
        return HttpResponse(f"Error al generar el PDF: {e}", status=500)


def generar_zip_recibos(request):
    """
    Toma una lista de PKs de recibos, genera el PDF de cada uno y los comprime en un ZIP.
    """
    pks_str = request.GET.get('pks')
    if not pks_str:
        messages.error(request, "No se encontraron IDs de recibos para generar el ZIP.")
        return redirect(reverse('recibos:dashboard'))

    try:
        pks = [int(pk) for pk in pks_str.split(',')]
        recibos = Recibo.objects.filter(pk__in=pks)
    except ValueError:
        messages.error(request, "Error en el formato de los IDs de recibos.")
        return redirect(reverse('recibos:dashboard'))
    except Exception as e:
        messages.error(request, f"Error al buscar recibos: {e}")
        return redirect(reverse('recibos:dashboard'))


    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for recibo in recibos:
            try:
                # 🛑 CORRECCIÓN: Usar la nueva utilidad de generación PDF unitaria
                pdf_response = generar_pdf_recibo_unitario(recibo) 
                
                # Extraer el contenido (bytes) del HttpResponse
                pdf_buffer_value = pdf_response.content 

                num_recibo_zfill = str(recibo.numero_recibo).zfill(4) if recibo.numero_recibo else '0000'
                filename = f"Recibo_N_{num_recibo_zfill}_{recibo.rif_cedula_identidad}.pdf"

                zipf.writestr(filename, pdf_buffer_value)
            except Exception as e:
                logger.error(f"Error al generar el PDF para el recibo PK={recibo.pk}: {e}")


    zip_buffer.seek(0)

    filename_zip = f"Recibos_Masivos_{timezone.now().strftime('%Y%m%d_%H%M%S')}.zip"
    response = HttpResponse(
        zip_buffer.getvalue(),
        content_type='application/zip'
    )
    response['Content-Disposition'] = f'attachment;filename="{filename_zip}"'

    return response


class ReciboListView(ListView):
    model = Recibo
    template_name = 'recibos/dashboard.html'
    context_object_name = 'recibos'
    paginate_by = 20

    def post(self, request, *args, **kwargs):
        """Maneja todas las acciones POST: Carga de Excel, Anulación, Limpieza."""
        action = request.POST.get('action')

        if action == 'anular':
            recibo_id = request.POST.get('recibo_id')
            if recibo_id:
                recibo = get_object_or_404(Recibo, pk=recibo_id)
                if not recibo.anulado:

                    num_recibo_zfill = str(recibo.numero_recibo).zfill(4) if recibo.numero_recibo else '0000'

                    recibo.anulado = True
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
                    success, message, recibos_pks = importar_recibos_desde_excel(archivo_excel)

                    if success and recibos_pks and isinstance(recibos_pks, list):
                        messages.success(request, message)

                        if len(recibos_pks) == 1:
                            # ✅ CORRECCIÓN CLAVE: Redirigir a la vista de descarga directa (generar_pdf_recibo)
                            return redirect(reverse('recibos:generar_pdf_recibo', kwargs={'pk': recibos_pks[0]})) 
                        else:
                            pks_str = ','.join(map(str, recibos_pks))
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

        if search_query:
            query_normalizado = search_query.strip()

            if search_field and search_field != 'todos':
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
                    q_objects |= Q(id=recibo_id)
                except ValueError:
                    pass

                queryset = queryset.filter(q_objects)

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

        category_filters = Q()
        for codigo, _ in CATEGORY_CHOICES:
            if self.request.GET.get(codigo) == 'on':
                category_filters |= Q(**{f'{codigo}': True})

        if category_filters:
            queryset = queryset.filter(category_filters)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

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

        request_get_copy = self.request.GET.copy()
        if 'page' in request_get_copy:
            del request_get_copy['page']

        if 'q' in request_get_copy and not request_get_copy['q']:
            del request_get_copy['q']
        if 'field' in request_get_copy and not request_get_copy['field']:
            del request_get_copy['field']

        context['request_get'] = request_get_copy

        return context


def generar_reporte_view(request):
    recibos_queryset = Recibo.objects.filter(anulado=False).order_by('-fecha', '-numero_recibo')

    filters = Q()
    filtros_aplicados = {}
    periodo_str = 'Todas las fechas'

    estado_seleccionado = request.GET.get('estado')

    if estado_seleccionado and estado_seleccionado != "":
        filters &= Q(estado__iexact=estado_seleccionado)
    filtros_aplicados['estado'] = estado_seleccionado if estado_seleccionado else 'Todos los estados'

    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')

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

    selected_categories_names = []
    category_filters = Q()
    category_count = 0

    for codigo, nombre_display in CATEGORY_CHOICES:
        if request.GET.get(codigo) == 'on':
            category_filters |= Q(**{f'{codigo}': True})
            selected_categories_names.append(nombre_display)
            category_count += 1

    if category_count > 0:
        filters &= category_filters
        filtros_aplicados['categorias'] = ','.join(selected_categories_names)
    else:
        filtros_aplicados['categorias'] = 'Todas las categorías'

    search_query = request.GET.get('q')
    search_field = request.GET.get('field', '')

    if search_query:
        query_normalizado = search_query.strip()

        if search_field and search_field != 'todos':
            try:
                filtro = {f'{search_field}__icontains': query_normalizado}
                filters &= Q(**filtro)
            except Exception:
                pass
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
                q_objects |= Q(id=recibo_id)
            except ValueError:
                pass
            filters &= q_objects

        filtros_aplicados['busqueda'] = search_query
    else:
        filtros_aplicados['busqueda'] = 'Ninguna'


    recibos_filtrados = recibos_queryset.filter(filters)

    action = request.GET.get('action')

    if action == 'excel':
        try:
            return generar_reporte_excel(request.GET, recibos_filtrados, filtros_aplicados)
        except Exception as e:
            logger.error(f"Error al generar el reporte Excel: {e}")
            messages.error(request, f"Error al generar el reporte Excel: {e}")
            return redirect(reverse('recibos:dashboard') + '?' + request.GET.urlencode())

    elif action == 'pdf':
        try:
            return generar_pdf_reporte(recibos_filtrados, filtros_aplicados)
        except Exception as e:
            logger.error(f"Error al generar el reporte PDF: {e}")
            messages.error(request, f"Error al generar el reporte PDF. Consulte la consola del servidor: {e}")
            return redirect(reverse('recibos:dashboard') + '?' + request.GET.urlencode())

    else:
        messages.error(request, "Acción de reporte no válida.")
        return redirect(reverse('recibos:dashboard') + '?' + request.GET.urlencode())


def modificar_recibo(request, pk):
    """
    Permite modificar un Recibo existente (sino está anulado) o anularlo.
    """
    recibo = get_object_or_404(Recibo, pk=pk)

    num_recibo_zfill = str(recibo.numero_recibo).zfill(4) if recibo.numero_recibo else '0000'

    if recibo.anulado:
        messages.error(request, f"El recibo N°{num_recibo_zfill} se encuentra ANULADO y es irreversible. No se pueden realizar cambios.")
        return redirect(reverse('recibos:recibos_anulados'))

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'anular':
            recibo.anulado = True
            recibo.save()
            messages.warning(request, f"¡Recibo N°{num_recibo_zfill} ha sido ANULADO exitosamente! (Acción irreversible)")
            return redirect(reverse('recibos:recibos_anulados'))

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


def recibos_anulados(request):
    """
    Muestra exclusivamente la tabla de recibos que han sido anulados (anulado=True).
    """
    recibos_anulados_list = Recibo.objects.filter(anulado=True).order_by('-fecha_creacion')

    context = {
        'recibos': recibos_anulados_list,
        'titulo': 'Recibos Anulados',
    }
    return render(request, 'recibos/recibos_anulados.html', context)