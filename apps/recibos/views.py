from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, FileResponse
from django.db.models import Max, Q, Sum
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
# 🚀 AJUSTE DE IMPORTACIÓN: Cambiamos 'generar_excel_recibos' por 'generar_reporte_excel'
from .utils import importar_recibos_desde_excel, generar_reporte_excel, generar_pdf_reporte
from django.conf import settings
from django.core.paginator import Paginator
# 🚀 ADICIÓN DE CONSTANTES: Necesitamos los mapas para nombres legibles
from .constants import CATEGORY_CHOICES_MAP, CATEGORY_CHOICES, ESTADO_CHOICES_MAP

logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN DE IMAGEN DE ENCABEZADO ---
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
    # Ruta alternativa para desarrollo o entornos sin settings.BASE_DIR
    HEADER_IMAGE = os.path.join(os.path.dirname(__file__), '..', 'static', 'recibos', 'images', 'encabezado.png')


# --- FUNCIONES DE AYUDA (PDF) ---

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
        # Formatea a 2 decimales, usa 'X' temporalmente para la coma, luego reemplaza
        return "{:,.2f}".format(amount_decimal).replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00" 

def draw_centered_text_right(canvas_obj, y_pos, text, x_start, width, font_name="Helvetica", font_size=10, is_bold=False):
    """Centra el texto dentro de un ancho específico."""
    font = font_name + "-Bold" if is_bold else font_name
    canvas_obj.setFont(font, font_size)
    text_width = canvas_obj.stringWidth(text, font, font_size)
    x = x_start + (width - text_width) / 2
    canvas_obj.drawString(x, y_pos, text.upper())
    
def generate_receipt_pdf(recibo_obj):
    """Genera el contenido del PDF individual para un recibo."""
    nombre = recibo_obj.nombre
    cedula = recibo_obj.rif_cedula_identidad
    direccion = recibo_obj.direccion_inmueble
    monto = recibo_obj.total_monto_bs
    num_transf = recibo_obj.numero_transferencia if recibo_obj.numero_transferencia else ''
    fecha = recibo_obj.fecha.strftime("%d/%m/%Y")
    concepto = recibo_obj.concepto
    estado = recibo_obj.estado
    num_recibo = str(recibo_obj.numero_recibo)
    
    # Mapeo de categorías
    categorias = {
        f'categoria{i}': getattr(recibo_obj, f'categoria{i}') for i in range(1, 11)
    }
    
    monto_formateado = format_currency(monto)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    current_y = height - 50
    y_top = height - 50
    
    # Dibujar encabezado
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

    # Posiciones de columnas
    X1_TITLE = 60
    X1_DATA = 160 
    X2_TITLE = 310
    X2_DATA = 470
    
    # Dibujar detalles
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

    
    # --- Secciones de Categorías (Larga) ---
    hay_categorias = any(categorias.values())
    
    if hay_categorias:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(X1_TITLE, current_y, "FORMA DE PAGO Y DESCRIPCION DE LA REGULARIZACION")
        current_y -= 25

        if categorias.get('categoria1', False):
            current_y = draw_text_line(c, "TITULO DE TIERRA URBANA- TITULO DE ADJUDICACION EN PROPIEDAD", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line(c, "Una milésima de Bolívar, Art. 58 de la Ley Especial de Regularización", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5
        
        if categorias.get('categoria2', False):
            current_y = draw_text_line(c, "TITULO DE TIERRA URBANA-TITULO DE ADJUDICACION MAS VIVIENDA", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line(c, "Una milésima de Bolívar, más gastos administrativos(140 unidades ancladas a la moneda de mayor valor estipulada por el BCV)", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5
        
        if categorias.get('categoria3', False):
            current_y = draw_text_line(c, "VIVIENDA UNIFAMILIAR Y MULTIFAMILIAR(EDIFICIOS) TIERRA:", X1_TITLE, current_y, font_size=9, is_bold=True)
            current_y = draw_text_line(c, "Municipal", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line(c, "Precio: Gastos Administrativos(140 unidades ancladas a la moneda de mayor valor estipulada por el BCV)", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5

        if categorias.get('categoria4', False):
            current_y = draw_text_line(c, "VIVIENDA UNIFAMILIAR Y MULTIFAMILIAR(EDIFICIOS) TIERRA:", X1_TITLE, current_y, font_size=9, is_bold=True)
            current_y = draw_text_line(c, "Tierra Privada", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line(c, "Precio: Gastos Administrativos(140 unidades ancladas a la moneda de mayor valor estipulada por el BCV)", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5

        if categorias.get('categoria5', False):
            current_y = draw_text_line(c, "VIVIENDA UNIFAMILIAR Y MULTIFAMILIAR(EDIFICIOS) TIERRA:", X1_TITLE, current_y, font_size=9, is_bold=True)
            current_y = draw_text_line(c, "Tierra INAVI o de cualquier Ente transferido al INTU", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line(c, "Precio: Gastos Administrativos(140 unidades ancladas a la moneda de mayor valor estipulada por el BCV)", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5

        if categorias.get('categoria6', False):
            current_y = draw_text_line(c, "EXCEDENTES:", X1_TITLE, current_y, font_size=9, is_bold=True)
            current_y = draw_text_line(c, "Con título de Tierra Urbana, hasta 400 mt2 una milésima por mt2", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line(c, "Según el Art 33 de la Ley Especial de Regularización", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5

        if categorias.get('categoria7', False):
            current_y = draw_text_line(c, "Con Título INAVI(Gastos Administrativos):", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line(c, "140 unidades ancladas a la moneda de mayor valor estipulada por el BCV)", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5

        if categorias.get('categoria8', False):
            current_y = draw_text_line(c, "ESTUDIOS TÉCNICO:", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line(c, "Medición detallada de la parcela para obtener representación gráfica(plano)", X1_TITLE, current_y, font_size=8, is_bold=False)
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
    
    # Salto de página si el contenido está muy abajo
    if current_y < 150:
        c.showPage()
        current_y = height - 100

    # Firmas
    line_width = 200
    left_line_x = (width / 2 - line_width - 20)
    right_line_x = (width / 2 + 20)
    
    c.line(left_line_x, current_y, left_line_x + line_width, current_y)
    c.line(right_line_x, current_y, right_line_x + line_width, current_y)
    
    # Firma del contribuyente
    y_sig = current_y - 15 
    draw_centered_text_right(c, y_sig, "Firma", left_line_x, line_width) 
    y_sig -= 13 
    draw_centered_text_right(c, y_sig, nombre, left_line_x, line_width, is_bold=True)
    y_sig -= 12 
    draw_centered_text_right(c, y_sig, f"C.I./RIF: {cedula}", left_line_x, line_width, font_size=9)

    # Firma del receptor
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
    # Asegúrate de que esta función existe y devuelve un buffer (BytesIO)
    buffer = generate_receipt_pdf(recibo_obj) 
    filename = f"Recibo_N_{recibo_obj.numero_recibo}.pdf"
    
    response = HttpResponse(
        buffer.getvalue(), 
        content_type='application/pdf'
    )
    # Solo el encabezado de adjunto
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

# 2. Función Intermedia para forzar la Descarga y el Refresco
def init_download_and_refresh(request, pk):
    """Renderiza una plantilla con JS que inicia la descarga y redirige."""
    context = {
        'recibo_pk': pk,
        # Pasamos la URL del PDF real a la plantilla JS
        'pdf_url': reverse('recibos:generar_pdf_recibo', kwargs={'pk': pk})
    }
    # Asegúrate de tener una plantilla llamada 'download_init.html'
    return render(request, 'recibos/download_init.html', context)
# --- VISTA PRINCIPAL (UNIFICADA) ---

def dashboard_view(request):
    """
    Vista principal que maneja:
    1. Lógica POST (Importación de Excel, Anulación, Limpieza).
    2. Lógica GET (Filtrado, Búsqueda, Paginación).
    """
    TEMPLATE_NAME = 'recibos/dashboard.html'
    
    # ----------------------------------------------------
    # LÓGICA DE POST
    # ----------------------------------------------------
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'anular':
            recibo_id = request.POST.get('recibo_id') 
            if recibo_id:
                recibo = get_object_or_404(Recibo, pk=recibo_id) 
                if not recibo.anulado: 
                    recibo.anulado = True
                    recibo.estado = 'Anulado' 
                    recibo.save()
                    messages.success(request, f"El recibo N° {recibo.numero_recibo} ha sido ANULADO correctamente.")
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
                    # ESTE ES EL PUNTO CLAVE: Llama a la función que devuelve tres valores.
                    success, message, nuevo_recibo_id = importar_recibos_desde_excel(archivo_excel) 
                    
                    if success and nuevo_recibo_id:
                        messages.success(request, f"Importación exitosa. Recibo N° {Recibo.objects.get(pk=nuevo_recibo_id).numero_recibo}. Generado")
                        
                        # ¡REDIRECCIÓN CLAVE A LA VISTA INTERMEDIA!
                        return redirect(reverse('recibos:init_download', kwargs={'pk': nuevo_recibo_id}))
                    
                    elif success:
                        messages.warning(request, "Importación exitosa, pero no se generó un nuevo recibo para descargar.")
                    else:
                        messages.error(request, f"Fallo en la carga de Excel: {message}")
                except Exception as e:
                    logger.error(f"Error al ejecutar la importación de Excel: {e}")
                    messages.error(request, f"Error interno en la lógica de importación: {e}")
            
            # Si hay un error, redirecciona al dashboard (GET)
            return redirect(reverse('recibos:dashboard'))


    # LÓGICA DE GET (FILTRADO Y BÚSQUEDA)
    
    queryset = Recibo.objects.all().order_by('-fecha', '-numero_recibo')

    # 1. Obtener estados disponibles (para el selectbox)
    estados_disponibles = Recibo.objects.exclude(
        estado__isnull=True
    ).exclude(
        estado__exact=''
    ).values_list(
        'estado', flat=True
    ).distinct().order_by('estado')

    # Filtro 1: Estado Geográfico
    estado_seleccionado = request.GET.get('estado')
    if estado_seleccionado and estado_seleccionado != "":
        queryset = queryset.filter(estado__iexact=estado_seleccionado) 

    # Filtro 2: Rango de Fechas
    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')
    
    try:
        if fecha_inicio_str:
            queryset = queryset.filter(fecha__gte=fecha_inicio_str)
        
        if fecha_fin_str:
            queryset = queryset.filter(fecha__lte=fecha_fin_str)
    except ValueError:
        pass 
        
    # Filtro 3: Categorías (Checkboxes)
    for codigo, _ in CATEGORY_CHOICES: 
        if request.GET.get(codigo) == 'on':
            queryset = queryset.filter(**{f'{codigo}': True})
    
    # Filtro 4: BÚSQUEDA GENERAL (q) - Corregido y Alineado
    search_query = request.GET.get('q')
    if search_query:
        query_normalizado = search_query.strip() 
        
        q_objects = (
            Q(nombre__icontains=search_query) |            
            Q(rif_cedula_identidad__icontains=query_normalizado) | 
            Q(numero_recibo__iexact=query_normalizado) | 
            Q(numero_transferencia__icontains=query_normalizado) |
            Q(estado__icontains=search_query)
        )
        try:
            recibo_id = int(search_query.strip())
            q_objects |= Q(id=recibo_id)
        except ValueError:
            pass
        
        queryset = queryset.filter(q_objects)
    
    paginator = Paginator(queryset, 20)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'recibos': page_obj,  
        'page_obj': page_obj, 
        'estados_db': estados_disponibles, 
        'categorias_list': CATEGORY_CHOICES, 
        'current_estado': estado_seleccionado, 
        'current_start_date': fecha_inicio_str,
        'current_end_date': fecha_fin_str,
        'request_get': request.GET # Contiene todos los filtros actuales (útil para reportes)
    }
    
    return render(request, TEMPLATE_NAME, context)



def generar_reporte_view(request):
    """
    Recibe los parámetros GET, aplica el mismo filtrado que el dashboard,
    prepara los metadatos y genera un archivo Excel o PDF.
    """
    
    # 1. Inicializar QuerySet y Metadatos
    recibos_queryset = Recibo.objects.all().order_by('-fecha', '-numero_recibo')
    filters = Q()
    
    # Diccionario para la hoja 'info_reporte' (Metadatos legibles)
    filtros_aplicados = {}

    # 2. Aplicar Filtros (Alineado con dashboard_view)

    # Filtro 1: Estado Geográfico
    estado_seleccionado = request.GET.get('estado')
    if estado_seleccionado and estado_seleccionado != "":
        # Aplicar filtro al QuerySet
        filters &= Q(estado__iexact=estado_seleccionado)
        # Guardar valor legible para el reporte
        filtros_aplicados['estado'] = estado_seleccionado # Usamos el valor directo o el mapeo si es un código
    else:
         filtros_aplicados['estado'] = 'Todos los estados'
        
    # Filtro 2: Rango de Fechas (Período)
    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')
    
    periodo_str = 'Todas las fechas'
    
    try:
        if fecha_inicio_str:
            filters &= Q(fecha__gte=fecha_inicio_str)
            periodo_str = f"Desde: {fecha_inicio_str}"
        
        if fecha_fin_str:
            filters &= Q(fecha__lte=fecha_fin_str)
            periodo_str = f"{periodo_str} Hasta: {fecha_fin_str}"
            
    except ValueError:
        pass 
        
    filtros_aplicados['periodo'] = periodo_str.replace('Todas las fechas Hasta: None', 'Todas las fechas') # Limpieza si solo hay fecha_fin


    # Filtro 3: Categorías
    selected_categories_names = []
    category_filters = Q()
    category_count = 0

    for codigo, nombre_display in CATEGORY_CHOICES: 
        if request.GET.get(codigo) == 'on':
            # Aplicar filtro al QuerySet
            category_filters |= Q(**{f'{codigo}': True})
            # Guardar valor legible para el reporte
            selected_categories_names.append(nombre_display)
            category_count += 1
            
    if category_count > 0:
        filters &= category_filters
        filtros_aplicados['categorias'] = ', '.join(selected_categories_names)
    else:
        filtros_aplicados['categorias'] = 'Todas las categorías'
    
    # Filtro 4: BÚSQUEDA GENERAL (q)
    search_query = request.GET.get('q')
    if search_query:
        query_normalizado = search_query.strip() 
        # ... (La lógica Q de búsqueda se mantiene igual y se aplica a 'filters') ...
        q_objects = (
             Q(nombre__icontains=search_query) |            
             Q(rif_cedula_identidad__icontains=query_normalizado) | 
             Q(numero_recibo__iexact=query_normalizado) | 
             Q(numero_transferencia__icontains=query_normalizado) |
             Q(estado__icontains=search_query)
         )
        try:
             recibo_id = int(search_query.strip())
             q_objects |= Q(id=recibo_id)
        except ValueError:
             pass
        filters &= q_objects
        filtros_aplicados['busqueda'] = search_query
    
    # 3. Obtener el QuerySet final
    recibos_filtrados = recibos_queryset.filter(filters)
    
    # 4. Determinar Acción (Excel vs. PDF)
    action = request.GET.get('action') 
    
    if action == 'excel':
        # 🚀 LÓGICA CLAVE: Llamar a la función de utilidad con los metadatos
        try:
            return generar_reporte_excel(request.GET, recibos_filtrados, filtros_aplicados)
        except Exception as e:
            logger.error(f"Error al generar el reporte Excel: {e}")
            messages.error(request, f"Error al generar el reporte Excel: {e}")
            return redirect(reverse('recibos:dashboard') + '?' + request.GET.urlencode())

    elif action == 'pdf':
        # ❌ Mantenemos el PDF deshabilitado o con la lógica existente (si ya está funcionando)
        # Si la implementación actual es funcional (usa ReportLab), la dejamos. 
        # Si NO ES FUNCIONAL para reporte masivo, se recomienda:
        messages.error(request, "La generación de Reporte PDF masivo aún no está implementada completamente (Formato Estructurado).")
        return redirect(reverse('recibos:dashboard') + '?' + request.GET.urlencode())
        
        # O si deseas usar la versión base, déjala como está:
        # try:
        #     return generar_pdf_reporte(recibos_filtrados) 
        # except Exception as e:
        #     messages.error(request, f"Error al generar el reporte PDF: {e}")
        #     return redirect(reverse('recibos:dashboard') + '?' + request.GET.urlencode())
            
    else:
        messages.error(request, "Acción de reporte no válida.")
        return redirect(reverse('recibos:dashboard') + '?' + request.GET.urlencode())