from django.shortcuts import render, redirect
from django.http import HttpResponse, FileResponse
from django.db.models import Max
from django.contrib import messages
from .models import Recibo 
import io
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from decimal import Decimal
import logging
from .utils import importar_recibos_desde_excel 
from django.conf import settings # 💡 NECESARIO PARA LA RUTA ABSOLUTA

logger = logging.getLogger(__name__)

# 💡 CORRECCIÓN DE RUTA CRÍTICA: Definición de la ruta absoluta del encabezado.
# Esto asegura que ReportLab (el generador de PDF) pueda encontrar la imagen.
try:
    # Esta ruta está construida asumiendo la estructura: 
    # [BASE_DIR]/apps/recibos/static/recibos/images/encabezado.png
    # 🚨 AJUSTA el segmento 'apps'/'recibos' si tu app está en otra ubicación (ej: sólo 'recibos')
    HEADER_IMAGE = os.path.join(
        settings.BASE_DIR, 
        'apps', 
        'recibos', 
        'static', 
        'recibos', 
        'images', 
        'encabezado.png' # <-- Nombre de archivo corregido
    )
except AttributeError:
    # Fallback si por alguna razón settings.BASE_DIR no está disponible
    HEADER_IMAGE = os.path.join(os.path.dirname(__file__), '..', 'static', 'recibos', 'images', 'encabezado.png')


# 1. FUNCIONES AUXILIARES DE PDF (Permanecen sin cambios excepto el uso de HEADER_IMAGE)

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
    nombre = recibo_obj.nombre
    cedula = recibo_obj.rif_cedula_identidad
    direccion = recibo_obj.direccion_inmueble
    monto = recibo_obj.total_monto_bs
    num_transf = recibo_obj.numero_transferencia if recibo_obj.numero_transferencia else ''
    fecha = recibo_obj.fecha.strftime("%d/%m/%Y")
    concepto = recibo_obj.concepto
    estado = 'ANULADO' if recibo_obj.anulado else 'ACTIVO'
    num_recibo = str(recibo_obj.numero_recibo)
    
    categorias = {
        f'categoria{i}': getattr(recibo_obj, f'categoria{i}') for i in range(1, 11)
    }
    
    monto_formateado = format_currency(monto)

    # 1. Crear el Canvas en memoria
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    current_y = height - 50
    y_top = height - 50
    
    # 💡 Lógica de carga de imagen usando la ruta corregida (HEADER_IMAGE)
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

    current_y = draw_text_line(c, "Recibí de:", X1_TITLE, current_y, is_bold=True)
    draw_text_line(c, nombre, X1_DATA, current_y + 15, is_bold=False)
    draw_text_line(c, "Monto Recibido (Bs.):", X2_TITLE, current_y + 15, is_bold=True)
    draw_text_line(c, monto_formateado, X2_DATA, current_y + 15, is_bold=False)

    current_y = draw_text_line(c, "Rif/C.I:", X1_TITLE, current_y, is_bold=True)
    draw_text_line(c, cedula, X1_DATA, current_y + 15, is_bold=False)
    current_y = draw_text_line(c, "Nº Transferencia:", X2_TITLE, current_y + 15, is_bold=True)
    draw_text_line(c, num_transf, X2_DATA, current_y + 15, is_bold=False)

    current_y = draw_text_line(c, "Dirección:", X1_TITLE, current_y, is_bold=True)
    draw_text_line(c, direccion, X1_DATA, current_y + 15, is_bold=False)
    draw_text_line(c, "Fecha:", X2_TITLE, current_y + 15, is_bold=True)
    draw_text_line(c, fecha, X2_DATA, current_y + 15, is_bold=False)
    
    current_y -= 10 
    current_y = draw_text_line(c, "Concepto:", X1_TITLE, current_y, is_bold=True)
    draw_text_line(c, concepto, X1_DATA, current_y + 15, is_bold=False)
    current_y -= 15

    
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
    
    if current_y < 150:
        c.showPage()
        current_y = height - 100

    line_width = 200
    left_line_x = (width / 2 - line_width - 20)
    right_line_x = (width / 2 + 20)
    
    c.line(left_line_x, current_y, left_line_x + line_width, current_y)
    c.line(right_line_x, current_y, right_line_x + line_width, current_y)
    current_y -= 12 

    y_sig = current_y + 12
    draw_centered_text_right(c, y_sig, "Firma", left_line_x, line_width) 
    y_sig -= 13
    draw_centered_text_right(c, y_sig, nombre, left_line_x, line_width, is_bold=True)
    y_sig -= 12
    draw_centered_text_right(c, y_sig, f"C.I./RIF: {cedula}", left_line_x, line_width, font_size=9)
    current_y = y_sig - 10 

    firma_y_instituto = current_y + 35 
    draw_centered_text_right(c, firma_y_instituto + 18, "Recibido por:", right_line_x, line_width)
    draw_centered_text_right(c, firma_y_instituto + 3, "PRESLEY ORTEGA", right_line_x, line_width, is_bold=True)
    draw_centered_text_right(c, firma_y_instituto - 10, "GERENTE DE ADMINISTRACIÓN Y SERVICIOS", right_line_x, line_width)
    draw_centered_text_right(c, firma_y_instituto - 25, "Designado según gaceta oficial n° 43.062 de fecha", right_line_x, line_width, font_size=8)
    draw_centered_text_right(c, firma_y_instituto - 35, "16 de febrero de 2025 y Providencia de", right_line_x, line_width, font_size=8)
    draw_centered_text_right(c, firma_y_instituto - 45, "n° 016-2024 de fecha 16 de diciembre de 2024", right_line_x, line_width, font_size=8)
    
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer 

# ----------------------------------------------------------------------
# 2. VISTAS PRINCIPALES (SE MANTIENEN EN LA VERSIÓN SIMPLE, EVITANDO EL PRG COMPLEJO)
# ----------------------------------------------------------------------

def crear_recibo_desde_excel(request):
    """
    Maneja la subida del archivo Excel y la descarga directa del PDF.
    NOTA: Este flujo de descarga directa impide que el mensaje de éxito se muestre
    y que el spinner se oculte automáticamente sin el patrón PRG completo.
    """
    TEMPLATE_NAME = 'recibos/dashboard.html'
    
    if request.method == 'POST':
        archivo_excel = request.FILES.get('archivo_recibo') 
        
        if not archivo_excel:
            messages.error(request, "Por favor, sube un archivo Excel con el nombre 'archivo_recibo'.")
            return render(request, TEMPLATE_NAME, {})

        try:
            success, message, nuevo_recibo_id = importar_recibos_desde_excel(archivo_excel) 
        except Exception as e:
            logger.error(f"Error al ejecutar la importación de Excel: {e}")
            messages.error(request, f"Error interno en la lógica de importación: {e}")
            return render(request, TEMPLATE_NAME, {})
        
        if success:
            try:
                if nuevo_recibo_id is None:
                    raise Recibo.DoesNotExist("La importación fue exitosa, pero no devolvió el ID del recibo creado.")
                    
                ultimo_recibo_obj = Recibo.objects.get(pk=nuevo_recibo_id) 
                
                pdf_buffer = generate_receipt_pdf(ultimo_recibo_obj)
                
                response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
                filename = f"Recibo_N_{ultimo_recibo_obj.numero_recibo}.pdf"
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                
                # Este mensaje se guarda en la sesión, pero NO se muestra porque la respuesta es un PDF.
                messages.success(request, f"Importación exitosa. Descargando recibo N° {ultimo_recibo_obj.numero_recibo}.")
                
                return response
            
            except Recibo.DoesNotExist:
                messages.error(request, "Error: La importación fue exitosa, pero no se pudo encontrar el recibo para generar el PDF.")
                return render(request, TEMPLATE_NAME, {})
            
            except Exception as e:
                logger.error(f"Error al generar el PDF: {e}")
                messages.error(request, f"Error crítico al generar el PDF: {e}")
                return render(request, TEMPLATE_NAME, {})

        else:
            messages.error(request, f"Fallo en la carga de Excel: {message}")
            return render(request, TEMPLATE_NAME, {})
            
    # Lógica GET normal
    try:
        context = {}
        # Asumiendo que quieres ver los últimos 20 recibos
        context['recibos'] = Recibo.objects.all().order_by('-fecha', '-numero_recibo')[:20] 
    except Exception:
        context = {'recibos': []}

    return render(request, TEMPLATE_NAME, context)


def descargar_pdf(request, pk):
    """
    Función de descarga. Asumo que se mantiene por si la necesitas para otros flujos.
    """
    try:
        recibo_obj = Recibo.objects.get(pk=pk)
    except Recibo.DoesNotExist:
        messages.error(request, "Error: El recibo solicitado para descarga no existe.")
        return redirect('dashboard')

    try:
        pdf_buffer = generate_receipt_pdf(recibo_obj)
        
        response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
        filename = f"Recibo_N_{recibo_obj.numero_recibo}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        logger.error(f"Error al generar el PDF de descarga: {e}")
        messages.error(request, f"Error al generar el PDF: {e}")
        return redirect('dashboard')

# Las funciones anular_recibo y editar_recibo (si existen) deben mantenerse o crearse.
# Por ejemplo:
# def anular_recibo(request, pk):
#     # ... lógica de anulación ...
#     return redirect('dashboard')
# 
# def editar_recibo(request, pk):
#     # ... lógica de edición ...
#     return render(request, 'recibos/editar_recibo.html', {})