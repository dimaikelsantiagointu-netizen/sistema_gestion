from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, FileResponse
from django.db.models import Q
from django.contrib import messages
from .models import Recibo
import io
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from decimal import Decimal
import logging
from django.urls import reverse
from .utils import importar_recibos_desde_excel, generar_reporte_excel, generar_pdf_reporte
from django.conf import settings
from django.views.generic import ListView, TemplateView
from .forms import ReciboForm
from .constants import CATEGORY_CHOICES_MAP, CATEGORY_CHOICES, ESTADO_CHOICES_MAP

logger = logging.getLogger(__name__)

# --- Configuración de Imagen y Funciones de Utilidad PDF (Mantenidas) ---

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
    # Fallback si settings.BASE_DIR no está disponible o la ruta es relativa
    HEADER_IMAGE = os.path.join(os.path.dirname(__file__), '..', 'static', 'recibos', 'images', 'encabezado.png')

#para volver a la pagina incial base
class PaginaBaseView(TemplateView):
    template_name = 'base.html'
    
def draw_text_line(canvas_obj, text, x_start, y_start, font_name="Helvetica", font_size=10, is_bold=False):
    """Dibuja una línea de texto y ajusta la posición Y."""
    font = font_name + "-Bold" if is_bold else font_name
    canvas_obj.setFont(font, font_size)
    canvas_obj.drawString(x_start, y_start, str(text))
    return y_start - 15

def format_currency(amount):
    """Formatea el monto como moneda (ej: 1.234,56)."""
    try:
        amount_decimal = Decimal(amount)
        # Formato ES/LATAM: punto para miles, coma para decimales
        formatted = "{:,.2f}".format(amount_decimal)
        # Reemplazar la coma del formato en-US (miles) por 'X' temporalmente, el punto (decimal) por coma, y luego 'X' por punto.
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00"

def draw_centered_text_right(canvas_obj, y_pos, text, x_start, width, font_name="Helvetica", font_size=10, is_bold=False):
    """Centra el texto dentro de un ancho específico."""
    font = font_name + "-Bold" if is_bold else font_name
    canvas_obj.setFont(font, font_size)
    text_width = canvas_obj.stringWidth(text, font, font_size)
    x = x_start + (width - text_width) / 2
    canvas_obj.drawString(x, y_pos, text.upper())

# La función generate_receipt_pdf se mantiene sin cambios en su lógica.
def generate_receipt_pdf(recibo_obj):
    """Genera el contenido del PDF individual para un recibo."""
    #...(Se mantiene la lógica original de tu código para ReportLab)...
    nombre = recibo_obj.nombre
    cedula = recibo_obj.rif_cedula_identidad
    direccion = recibo_obj.direccion_inmueble
    monto = recibo_obj.total_monto_bs
    num_transf = recibo_obj.numero_transferencia if recibo_obj.numero_transferencia else ''
    fecha = recibo_obj.fecha.strftime("%d/%m/%Y")
    concepto = recibo_obj.concepto
    estado = recibo_obj.estado
    num_recibo = str(recibo_obj.numero_recibo)

    categorias = {
        f'categoria{i}': getattr(recibo_obj, f'categoria{i}') for i in range(1, 11)
    }

    monto_formateado = format_currency(monto)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    current_y = height - 50
    y_top = height - 50

    # Lógica de carga de imagen de encabezado
    if os.path.exists(HEADER_IMAGE):
        try:
            img = ImageReader(HEADER_IMAGE)
            img_width, img_height = img.getSize()
            scale = min(1.0, 480 / img_width)
            draw_width = img_width * scale
            draw_height = img_height * scale
            x_center = (width - draw_width) / 2
            y_top = height - draw_height - 20
            c.drawImage(HEADER_IMAGE, x=x_center, y=y_top, width=draw_width, height=draw_height)
            current_y = y_top - 25
        except Exception as e:
            logger.error(f"⚠️ Error cargando encabezado: {e}")

    c.setFont("Helvetica-Bold", 13)
    titulo_texto = "RECIBO DE PAGO"
    titulo_width = c.stringWidth(titulo_texto, "Helvetica-Bold", 13)
    titulo_x = (width - titulo_width) / 2
    c.drawString(titulo_x, current_y, titulo_texto)
    current_y -= 25

    X1_TITLE = 60
    X1_DATA = 160
    X2_TITLE = 310
    X2_DATA = 470

    current_y = draw_text_line(c, "Estado:", X1_TITLE, current_y, is_bold=True)
    draw_text_line(c, estado, X1_DATA, current_y + 15, is_bold=False)
    draw_text_line(c, "Nº Recibo:", X2_TITLE, current_y + 15, is_bold=True)
    draw_text_line(c, num_recibo, X2_DATA, current_y + 15, is_bold=False)
    current_y -= 5

    current_y = draw_text_line(c, "Recibí de:", X1_TITLE, current_y, is_bold=True)
    draw_text_line(c, nombre, X1_DATA, current_y + 15, is_bold=False)
    draw_text_line(c, "Monto Recibido (Bs.):", X2_TITLE, current_y + 15, is_bold=True)
    draw_text_line(c, monto_formateado, X2_DATA, current_y + 15, is_bold=False)
    current_y -= 5

    current_y = draw_text_line(c, "Rif/C.I:", X1_TITLE, current_y, is_bold=True)
    draw_text_line(c, cedula, X1_DATA, current_y + 15, is_bold=False)
    current_y = draw_text_line(c, "Nº Transferencia:", X2_TITLE, current_y + 15, is_bold=True)
    draw_text_line(c, num_transf, X2_DATA, current_y + 15, is_bold=False)
    current_y -= 5

    current_y = draw_text_line(c, "Dirección:", X1_TITLE, current_y, is_bold=True)
    draw_text_line(c, direccion, X1_DATA, current_y + 15, is_bold=False)
    draw_text_line(c, "Fecha:", X2_TITLE, current_y + 15, is_bold=True)
    draw_text_line(c, fecha, X2_DATA, current_y + 15, is_bold=False)
    current_y -= 5

    current_y = draw_text_line(c, "Concepto:", X1_TITLE, current_y, is_bold=True)
    draw_text_line(c, concepto, X1_DATA, current_y + 15, is_bold=False)
    current_y -= 15

    hay_categorias = any(categorias.values())

    if hay_categorias:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(X1_TITLE, current_y, "FORMA DE PAGO Y DESCRIPCION DE LA REGULARIZACION")
        current_y -= 25

        if categorias.get('categoria1', False):
            current_y = draw_text_line(c, "TITULO DE TIERRA URBANA - TITULO DE ADJUDICACION EN PROPIEDAD", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line(c, "Una milésima de Bolívar, Art. 58 de la Ley Especial de Regularización", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5

        if categorias.get('categoria2', False):
            current_y = draw_text_line(c, "TITULO DE TIERRA URBANA - TITULO DE ADJUDICACION MAS VIVIENDA", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line(c, "Una milésima de Bolívar, más gastos administrativos (140 unidades ancladas a la moneda de mayor valor estipulada por el BCV)", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5

        if categorias.get('categoria3', False):
            current_y = draw_text_line(c, "VIVIENDA UNIFAMILIAR Y MULTIFAMILIAR (EDIFICIOS) TIERRA:", X1_TITLE, current_y, font_size=9, is_bold=True)
            current_y = draw_text_line(c, "Municipal", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line(c, "Precio: Gastos Administrativos (140 unidades ancladas a la moneda de mayor valor estipulada por el BCV)", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5

        if categorias.get('categoria4', False):
            current_y = draw_text_line(c, "VIVIENDA UNIFAMILIAR Y MULTIFAMILIAR (EDIFICIOS) TIERRA:", X1_TITLE, current_y, font_size=9, is_bold=True)
            current_y = draw_text_line(c, "Tierra Privada", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line(c, "Precio: Gastos Administrativos (140 unidades ancladas a la moneda de mayor valor estipulada por el BCV)", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5

        if categorias.get('categoria5', False):
            current_y = draw_text_line(c, "VIVIENDA UNIFAMILIAR Y MULTIFAMILIAR (EDIFICIOS) TIERRA:", X1_TITLE, current_y, font_size=9, is_bold=True)
            current_y = draw_text_line(c, "Tierra INAVI o de cualquier Ente transferido al INTU", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line(c, "Precio: Gastos Administrativos (140 unidades ancladas a la moneda de mayor valor estipulada por el BCV)", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5

        if categorias.get('categoria6', False):
            current_y = draw_text_line(c, "EXCEDENTES:", X1_TITLE, current_y, font_size=9, is_bold=True)
            current_y = draw_text_line(c, "Con título de Tierra Urbana, hasta 400 mt2 una milésima por mt2", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line(c, "Según el Art 33 de la Ley Especial de Regularización", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5

        if categorias.get('categoria7', False):
            current_y = draw_text_line(c, "Con Título INAVI (Gastos Administrativos):", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line(c, "140 unidades ancladas a la moneda de mayor valor estipulada por el BCV)", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5

        if categorias.get('categoria8', False):
            current_y = draw_text_line(c, "ESTUDIOS TÉCNICO:", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line(c, "Medición detallada de la parcela para obtener representación gráfica (plano)", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5

        if categorias.get('categoria9', False):
            current_y = draw_text_line(c, "ARRENDAMIENTOS DE LOCALES COMERCIALES:", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line(c, "Número de unidades establecidas en el contrato, ancladas a la moneda de mayor valor estipulada por el BCV", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5

        if categorias.get('categoria10', False):
            current_y = draw_text_line(c, "ARRENDAMIENTOS DE TERRENOS", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line(c, "Número de unidades establecidas en el contrato, ancladas a la moneda de mayor valor estipulada por el BCV", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5

        current_y -= 70

    if current_y < 150:
        c.showPage()
        current_y = height - 100

    line_width = 200
    left_line_x = (width / 2 - line_width - 20)
    right_line_x = (width / 2 + 20)

    c.line(left_line_x, current_y, left_line_x + line_width, current_y)
    c.line(right_line_x, current_y, right_line_x + line_width, current_y)

    y_sig = current_y - 15
    draw_centered_text_right(c, y_sig, "Firma", left_line_x, line_width)
    y_sig -= 13
    draw_centered_text_right(c, y_sig, nombre, left_line_x, line_width, is_bold=True)
    y_sig -= 12
    draw_centered_text_right(c, y_sig, f"C.I./RIF: {cedula}", left_line_x, line_width, font_size=9)

    y_sig_inst = current_y - 15
    draw_centered_text_right(c, y_sig_inst, "Recibido por:", right_line_x, line_width)
    y_sig_inst -= 13
    draw_centered_text_right(c, y_sig_inst, "PRESLEY ORTEGA", right_line_x, line_width, is_bold=True)
    y_sig_inst -= 12
    draw_centered_text_right(c, y_sig_inst, "GERENTE DE ADMINISTRACIÓN Y SERVICIOS", right_line_x, line_width, font_size=9)
    y_sig_inst -= 15
    draw_centered_text_right(c, y_sig_inst, "Designado según gaceta oficial n° 43.062 de fecha", right_line_x, line_width, font_size=8)
    y_sig_inst -= 10
    draw_centered_text_right(c, y_sig_inst, "16 de febrero de 2025 y Providencia de", right_line_x, line_width, font_size=8)
    y_sig_inst -= 10
    draw_centered_text_right(c, y_sig_inst, "n° 016-2024 de fecha 16 de diciembre de 2024", right_line_x, line_width, font_size=8)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


def generar_pdf_recibo(request, pk):
    """Genera y devuelve el PDF puro para la descarga."""
    recibo_obj = get_object_or_404(Recibo, pk=pk)
    buffer = generate_receipt_pdf(recibo_obj)
    filename = f"Recibo_N_{recibo_obj.numero_recibo}.pdf"

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/pdf'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

def init_download_and_refresh(request, pk):
    """Renderiza una plantilla con JS que inicia la descarga y redirige."""
    context = {
        'recibo_pk': pk,
        'pdf_url': reverse('recibos:generar_pdf_recibo', kwargs={'pk': pk})
    }
    return render(request, 'recibos/download_init.html', context)


# --- VISTA BASADA EN CLASES (ListView) ---
class ReciboListView(ListView):
    model = Recibo
    template_name = 'recibos/dashboard.html'
    context_object_name = 'recibos'
    paginate_by = 20 # FIJADO a 20 como requerido

    def post(self, request, *args, **kwargs):
        """Maneja todas las acciones POST: Carga de Excel, Anulación, Limpieza."""
        action = request.POST.get('action')

        # 1. ANULACIÓN (Nota: Esta lógica es redundante si solo usas el botón en modificar_recibo)
        # Se recomienda usar la función modificar_recibo para anular y eliminar esta lógica de aquí,
        # pero la mantenemos si tienes botones de anulación en el dashboard.
        if action == 'anular':
            recibo_id = request.POST.get('recibo_id')
            if recibo_id:
                recibo = get_object_or_404(Recibo, pk=recibo_id)
                # Aplicamos la lógica de anulación aquí
                if not recibo.anulado:
                    recibo.anulado = True
                    recibo.save()
                    messages.success(request, f"El recibo N°{recibo.numero_recibo} ha sido ANULADO correctamente.")
                else:
                    messages.warning(request, "Este recibo ya estaba anulado.")
            else:
                messages.error(request, "No se proporcionó el ID del recibo a anular.")
            return redirect(reverse('recibos:dashboard'))

        # 2. CLEAR LOGS (ELIMINACIÓN TOTAL)
        elif action == 'clear_logs': 
            # ADVERTENCIA: Esta acción borra *todos* los recibos de la BD, no solo los logs visuales.
            Recibo.objects.all().delete()
            messages.success(request, "Todos los recibos han sido eliminados de la base de datos.")
            return redirect(reverse('recibos:dashboard'))

        # 3. UPLOAD (Importación de Excel)
        elif action == 'upload':
            archivo_excel = request.FILES.get('archivo_recibo')
            if not archivo_excel:
                messages.error(request, "Por favor, sube un archivo Excel.")
            else:
                try:
                    # Asegúrate de que 'importar_recibos_desde_excel' esté disponible/importada
                    success, message, nuevo_recibo_id = importar_recibos_desde_excel(archivo_excel)

                    if success and nuevo_recibo_id:
                        messages.success(request, f"Importación exitosa. Recibo N°{Recibo.objects.get(pk=nuevo_recibo_id).numero_recibo}. Generado")
                        return redirect(reverse('recibos:init_download', kwargs={'pk': nuevo_recibo_id}))

                    elif success:
                        messages.warning(request, "Importación exitosa, pero no se generó un nuevo recibo para descargar.")
                    else:
                        messages.error(request, f"Fallo en la carga de Excel: {message}")
                except Exception as e:
                    logger.error(f"Error al ejecutar la importación de Excel: {e}")
                    messages.error(request, f"Error interno en la lógica de importación: {e}")

            return redirect(reverse('recibos:dashboard'))

        return redirect(reverse('recibos:dashboard'))


    def get_queryset(self):
        
        # 🌟🌟🌟 CAMBIO CLAVE: APLICAR FILTRO DE ANULADO=FALSE 🌟🌟🌟
        # La tabla principal SÓLO debe mostrar los recibos que NO han sido anulados.
        queryset = Recibo.objects.filter(anulado=False).order_by('-fecha', '-numero_recibo') 
        # NOTA: Eliminamos super().get_queryset() porque queremos partir del filtro inicial.
        
        # 2. FILTRO: Búsqueda General y Selectiva (q y field) 
        search_query = self.request.GET.get('q')
        search_field = self.request.GET.get('field', '') # Captura el campo a buscar

        if search_query:
            query_normalizado = search_query.strip()
            
            # Lógica para la Búsqueda Selectiva (si se eligió un campo)
            if search_field and search_field != 'todos': 
                try:
                    filtro = {f'{search_field}__icontains': query_normalizado}
                    queryset = queryset.filter(**filtro)
                except Exception as e:
                    logger.error(f"Error al filtrar por campo dinámico {search_field}: {e}")
                    
            # Lógica para la Búsqueda General
            else:
                q_objects = (
                    Q(nombre__icontains=query_normalizado) |
                    Q(rif_cedula_identidad__icontains=query_normalizado) |
                    Q(numero_recibo__iexact=query_normalizado) |
                    Q(numero_transferencia__icontains=query_normalizado) |
                    Q(estado__icontains=query_normalizado)
                )
                
                # Intenta buscar por ID si el query es un número
                try:
                    recibo_id = int(query_normalizado)
                    q_objects |= Q(id=recibo_id)
                except ValueError:
                    pass

                queryset = queryset.filter(q_objects)

        # 3. FILTRO: Estado (dropdown)
        estado_seleccionado = self.request.GET.get('estado')
        if estado_seleccionado and estado_seleccionado != "":
            queryset = queryset.filter(estado__iexact=estado_seleccionado)

        # 4. FILTRO: Rango de Fechas
        fecha_inicio_str = self.request.GET.get('fecha_inicio')
        fecha_fin_str = self.request.GET.get('fecha_fin')

        try:
            if fecha_inicio_str:
                queryset = queryset.filter(fecha__gte=fecha_inicio_str)
            if fecha_fin_str:
                queryset = queryset.filter(fecha__lte=fecha_fin_str)
        except ValueError:
            pass

        # 5. FILTRO: Categorías (Checkboxes)
        category_filters = Q()
        for codigo, _ in CATEGORY_CHOICES:
            if self.request.GET.get(codigo) == 'on':
                category_filters |= Q(**{f'{codigo}': True})

        if category_filters:
            queryset = queryset.filter(category_filters)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Datos para los filtros en el template (Mantenidos)
        # Nota: Aquí también se debería considerar filtrar por anulado=False si los estados son generados dinámicamente.
        context['estados_db'] = Recibo.objects.filter(anulado=False).exclude( # <--- Filtro agregado aquí también
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

        # Lógica corregida para pasar request_get excluyendo 'page'
        request_get_copy = self.request.GET.copy()
        if 'page' in request_get_copy:
            del request_get_copy['page']
        
        # Eliminamos 'q' y 'field' si están solos, para asegurar que la paginación no los repita incorrectamente.
        if 'q' in request_get_copy and not request_get_copy['q']:
            del request_get_copy['q']
        if 'field' in request_get_copy and not request_get_copy['field']:
            del request_get_copy['field']

        context['request_get'] = request_get_copy

        return context

# =======================================================
# FUNCIONES AUXILIARES (Modificar, Anulados, Reportes)
# =======================================================

def generar_reporte_view(request):
    # 🌟🌟 CAMBIO CLAVE: FILTRAR PARA EXCLUIR ANULADOS 🌟🌟
    # Aseguramos que solo se consideren los recibos que NO están anulados.
    recibos_queryset = Recibo.objects.filter(anulado=False).order_by('-fecha', '-numero_recibo')
    
    filters = Q()
    filtros_aplicados = {}
    periodo_str = 'Todas las fechas'
    
    # 1. Filtro de Estado
    estado_seleccionado = request.GET.get('estado')
    # ... (El resto de la lógica de filtros se mantiene igual) ...

    # 1. Filtro de Estado
    estado_seleccionado = request.GET.get('estado')
    if estado_seleccionado and estado_seleccionado != "":
        filters &= Q(estado__iexact=estado_seleccionado)
    filtros_aplicados['estado'] = estado_seleccionado if estado_seleccionado else 'Todos los estados'

    # 2. Filtro de Rango de Fechas
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
    
    # 3. Filtro de Categorías
    selected_categories_names = []
    category_filters = Q()
    category_count = 0

    # Nota: CATEGORY_CHOICES debe estar importado
    for codigo, nombre_display in CATEGORY_CHOICES: 
        if request.GET.get(codigo) == 'on':
            category_filters |= Q(**{f'{codigo}': True})
            selected_categories_names.append(nombre_display)
            category_count += 1

    if category_count > 0:
        filters &= category_filters
        filtros_aplicados['categorias'] = ', '.join(selected_categories_names)
    else:
        filtros_aplicados['categorias'] = 'Todas las categorías'
        
    # 4. Filtro de Búsqueda (q y field)
    search_query = request.GET.get('q')
    search_field = request.GET.get('field', '') 

    if search_query:
        query_normalizado = search_query.strip()
        
        # Búsqueda Selectiva
        if search_field and search_field != 'todos':
            try:
                filtro = {f'{search_field}__icontains': query_normalizado}
                filters &= Q(**filtro)
            except Exception:
                pass
        # Búsqueda General
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


    recibos_filtrados = recibos_queryset.filter(filters) # Aplica todos los filtros adicionales

    action = request.GET.get('action')

    if action == 'excel':
        try:
            # Asegúrate de que generar_reporte_excel esté disponible/importado
            return generar_reporte_excel(request.GET, recibos_filtrados, filtros_aplicados)
        except Exception as e:
            logger.error(f"Error al generar el reporte Excel: {e}")
            messages.error(request, f"Error al generar el reporte Excel: {e}")
            return redirect(reverse('recibos:dashboard') + '?' + request.GET.urlencode())

    elif action == 'pdf':
        try:
            # Asegúrate de que generar_pdf_reporte esté disponible/importado
            return generar_pdf_reporte(recibos_filtrados, filtros_aplicados)
        except Exception as e:
            logger.error(f"Error al generar el reporte PDF: {e}")
            messages.error(request, f"Error al generar el reporte PDF. Consulte la consola del servidor: {e}")
            return redirect(reverse('recibos:dashboard') + '?' + request.GET.urlencode())

    else:
        messages.error(request, "Acción de reporte no válida.")
        return redirect(reverse('recibos:dashboard') + '?' + request.GET.urlencode())

# ----------------------------------------------------------------------
# Funciones para la descarga individual (asume que ya existen)
# ----------------------------------------------------------------------
# def init_download_and_refresh(request, pk): ...
# def generar_pdf_recibo(request, pk): ...

# ----------------------------------------------------------------------
# Modificar Recibo y Anulación (Mantenido y Reconfirmado)
# ----------------------------------------------------------------------

def modificar_recibo(request, pk):
    """
    Permite modificar un Recibo existente (si no está anulado) o anularlo.
    """
    recibo = get_object_or_404(Recibo, pk=pk)
    
    # 1. REGLA DE INMUTABILIDAD: NO PERMITIR MODIFICAR NI PROCESAR SI ESTÁ ANULADO
    if recibo.anulado:
        messages.error(request, f"El recibo N°{recibo.numero_recibo} se encuentra ANULADO y es irreversible. No se pueden realizar cambios.")
        # Se redirige a la tabla de anulados para que el usuario pueda ver el registro.
        return redirect(reverse('recibos:recibos_anulados')) 

    if request.method == 'POST':
        action = request.POST.get('action') # 'modificar' o 'anular'

        # =======================================================
        # ACCIÓN 1: ANULAR EL RECIBO (Eliminación Lógica)
        # =======================================================
        if action == 'anular':
            recibo.anulado = True   # Campo 'anulado' en True
            # Opcional: Establecer un estado de 'Anulado' para reportes o rastreo
            # recibo.estado = 'Anulado' 
            recibo.save()
            messages.warning(request, f"¡Recibo N°{recibo.numero_recibo} ha sido ANULADO exitosamente! (Acción irreversible)")
            return redirect(reverse('recibos:recibos_anulados')) 

        # =======================================================
        # ACCIÓN 2: MODIFICAR EL RECIBO
        # =======================================================
        else: # Si action es 'modificar' o no está definido
            form = ReciboForm(request.POST, instance=recibo)
            
            if form.is_valid():
                form.save()
                messages.success(request, f"¡Recibo N°{recibo.numero_recibo} modificado exitosamente!")
                return redirect(reverse('recibos:dashboard'))
            else:
                messages.error(request, "Error al guardar los cambios. Por favor, revisa los campos.")

    # Manejo del GET
    else:
        form = ReciboForm(instance=recibo)

    context = {
        'recibo': recibo, 
        'form': form,     
    }
    
    return render(request, 'recibos/modificar_recibo.html', context)

# ----------------------------------------------------------------------
# Vista de Recibos Anulados (Mantenido y Reconfirmado)
# ----------------------------------------------------------------------
def recibos_anulados(request):
    """
    Muestra exclusivamente la tabla de recibos que han sido anulados (anulado=True).
    """
    recibos_anulados_list = Recibo.objects.filter(anulado=True).order_by('-fecha_creacion')
    
    context = {
        'recibos': recibos_anulados_list,
        'titulo': 'Recibos Anulados (Irreversibles)',
    }
    return render(request, 'recibos/recibos_anulados.html', context)