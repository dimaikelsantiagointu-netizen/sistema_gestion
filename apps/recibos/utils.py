import pandas as pd
from datetime import datetime
import textwrap
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from django.conf import settings
import os
from io import BytesIO

# --- Funciones de Utilidad de Procesamiento de Excel ---

def is_marked(val):
    """
    Verifica si el valor de una celda de Excel debe interpretarse como 'marcado' (True).
    Busca 'X', '1', 'True', 'Si', etc., ignorando mayúsculas y espacios.
    """
    if pd.isna(val):
        return False
    val_str = str(val).strip().lower()
    return val_str in ['x', '1', 'true', 'si', 'sí', 'yes', 'check', '✓']

def clean(val):
    """
    Limpia y normaliza el valor de una celda de Excel a una cadena de texto.
    Devuelve una cadena vacía si es NaN o None.
    """
    if pd.isna(val) or val is None:
        return ""
    # Aseguramos que el valor sea string antes de hacer strip
    return str(val).strip()

def format_date_for_db(fecha_str):
    """
    Convierte una cadena o tipo de fecha (Date/Timestamp) a formato 'YYYY-MM-DD' (PostgreSQL).
    Acepta múltiples formatos de entrada y usa la fecha actual si falla la conversión.
    """
    try:
        if isinstance(fecha_str, str) and fecha_str.strip():
            # Intentar analizar formatos comunes (DD/MM/YYYY, YYYY-MM-DD, etc.)
            for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%y', '%d-%m-%y']:
                try:
                    fecha_obj = datetime.strptime(fecha_str.strip(), fmt)
                    return fecha_obj.strftime('%Y-%m-%d')
                except ValueError:
                    continue
        if isinstance(fecha_str, (pd.Timestamp, datetime)):
            return fecha_str.strftime('%Y-%m-%d')
        # Fallback a la fecha actual si no se puede parsear
        return datetime.now().strftime('%Y-%m-%d')
    except:
        return datetime.now().strftime('%Y-%m-%d')

# --- Funciones de Generación de PDF (usando ReportLab) ---

def format_currency(value):
    """
    Formatea un valor numérico a Bs. con separador de miles (punto) y
    dos decimales (coma), siguiendo el formato venezolano.
    """
    try:
        # Limpiar y convertir a float
        cleaned = ''.join(c for c in str(value) if c.isdigit() or c in ',.')
        cleaned = cleaned.replace(',', '.') 
        amount = float(cleaned)
        
        # Formatear: punto como separador de miles, coma como decimal
        formatted = "{:,.2f}".format(amount).replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted
    except (ValueError, TypeError):
        return str(value) if value else "0,00"

def draw_wrapped_text(c, text, x, y, max_width, max_lines=3, font_size=9, is_bold=False, line_height=12):
    """
    Dibuja texto con ajuste de línea (word wrap) dentro de un ancho máximo.
    """
    if is_bold:
        c.setFont("Helvetica-Bold", font_size)
    else:
        c.setFont("Helvetica", font_size)
    
    # [.. Implementación de draw_wrapped_text, igual a la del draft anterior ..]
    chars_per_line = int(max_width / (font_size * 0.6))
    wrapper = textwrap.TextWrapper(width=chars_per_line)
    lines = []
    
    for line in text.split('\n'):
        lines.extend(wrapper.wrap(line))
    
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][:chars_per_line-3] + "..."
    
    for i, line in enumerate(lines):
        c.drawString(x, y - (i * line_height), line)
    
    return y - (len(lines) * line_height)

def draw_wrapped_name(c, text, x, y, max_width, font_size=10, is_bold=False, line_height=12):
    """
    Dibuja texto ajustado, centrado horizontalmente (usado para nombres de firma).
    """
    # [.. Implementación de draw_wrapped_name, igual a la del draft anterior ..]
    if is_bold:
        c.setFont("Helvetica-Bold", font_size)
    else:
        c.setFont("Helvetica", font_size)
    
    chars_per_line = int(max_width / (font_size * 0.6))
    wrapper = textwrap.TextWrapper(width=chars_per_line)
    lines = wrapper.wrap(text)
    
    for i, line in enumerate(lines):
        line_width = c.stringWidth(line, "Helvetica-Bold" if is_bold else "Helvetica", font_size)
        centered_x = x + (max_width - line_width) / 2
        c.drawString(centered_x, y - (i * line_height), line)
    
    return y - (len(lines) * line_height)

def generate_receipt_pdf(receipt_data):
    """
    Genera el recibo PDF completo a partir de una instancia del modelo Receipt (Recibo).
    Utiliza el motor ReportLab y la configuración de diseño del código original.
    El resultado se devuelve como un buffer BytesIO (archivo en memoria).
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter 
    
    # Desempaquetar datos del objeto Receipt (models.py)
    nombre = receipt_data.client_name
    cedula = receipt_data.client_id
    direccion = receipt_data.client_address
    monto = receipt_data.amount
    num_transf = receipt_data.transaction_number
    fecha = receipt_data.payment_date.strftime('%d/%m/%Y') 
    concepto = receipt_data.concept
    estado = receipt_data.status
    num_recibo = receipt_data.receipt_number
    categorias = receipt_data.get_categories_dict()
    
    monto_formateado = format_currency(monto)

    # Nota: Asume que tienes una carpeta static/images/ con un logo
    HEADER_IMAGE_PATH = os.path.join(settings.BASE_DIR, 'static', 'images', 'header_logo.png') 
    
    # === ENCABEZADO Y LOGO (Lógica de dibujo igual a la anterior) ===
    current_y = height - 50
    try:
        # [.. Lógica de dibujo de logo ..]
        if os.path.exists(HEADER_IMAGE_PATH):
            img = ImageReader(HEADER_IMAGE_PATH)
            img_width, img_height = img.getSize()
            scale = min(1.0, 480 / img_width) 
            draw_width = img_width * scale
            draw_height = img_height * scale
            x_center = (width - draw_width) / 2
            y_top = height - draw_height - 20
            c.drawImage(HEADER_IMAGE_PATH, x=x_center, y=y_top, width=draw_width, height=draw_height)
            current_y = y_top - 25
    except Exception:
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(width / 2, height - 40, "LOGO INSTITUCIONAL")
        current_y = height - 80

    c.setFont("Helvetica-Bold", 13)
    titulo_texto = "RECIBO DE PAGO"
    titulo_width = c.stringWidth(titulo_texto, "Helvetica-Bold", 13)
    titulo_x = (width - titulo_width) / 2
    c.drawString(titulo_x, current_y, titulo_texto)
    current_y -= 25

    # [.. Dibujo de campos de datos ..]
    draw_wrapped_text(c, "Estado:", 60, current_y, max_width=80, max_lines=2, is_bold=True)
    c.setFont("Helvetica", 9); c.drawString(140, current_y, estado)
    draw_wrapped_text(c, "Nº Recibo:", 310, current_y, max_width=150, max_lines=2, is_bold=True)
    c.setFont("Helvetica", 9); c.drawString(470, current_y, num_recibo)
    current_y -= 25

    draw_wrapped_text(c, "Recibí de:", 60, current_y, max_width=80, max_lines=2, is_bold=True)
    draw_wrapped_text(c, nombre, 140, current_y, max_width=150, max_lines=8)
    draw_wrapped_text(c, "Monto Recibido (Bs.):", 310, current_y, max_width=150, max_lines=2, is_bold=True)
    c.setFont("Helvetica", 9); c.drawString(470, current_y, monto_formateado)
    current_y -= 30

    draw_wrapped_text(c, "Rif/C.I:", 60, current_y, max_width=120, max_lines=2, is_bold=True)
    draw_wrapped_text(c, cedula, 140, current_y, max_width=120, max_lines=4)
    draw_wrapped_text(c, "Nº Transferencia:", 310, current_y, max_width=150, max_lines=2, is_bold=True)
    draw_wrapped_text(c, num_transf, 470, current_y, max_width=100, max_lines=2)
    current_y -= 30

    draw_wrapped_text(c, "Dirección:", 60, current_y, max_width=80, max_lines=2, is_bold=True)
    draw_wrapped_text(c, direccion, 140, current_y, max_width=150, max_lines=3)
    draw_wrapped_text(c, "Fecha:", 310, current_y, max_width=50, max_lines=1, is_bold=True)
    c.setFont("Helvetica", 9); c.drawString(470, current_y, fecha)
    current_y -= 30

    draw_wrapped_text(c, "Concepto:", 60, current_y, max_width=80, max_lines=2, is_bold=True)
    draw_wrapped_text(c, concepto, 140, current_y, max_width=400, max_lines=3)
    current_y -= 40

    # === SECCIÓN DE CATEGORÍAS ===
    if any(categorias.values()):
        draw_wrapped_text(c, "FORMA DE PAGO Y DESCRIPCION DE LA REGULARIZACION", 60, current_y, max_width=500, max_lines=2, is_bold=True)
        current_y -= 25

        def draw_category(y, title, description, category_key):
            """Función auxiliar para dibujar una categoría si está marcada."""
            if categorias.get(category_key):
                c.setFont("Helvetica-Bold", 9)
                c.drawString(60, y, title)
                c.drawString(520, y, "X")
                y -= 14
                c.setFont("Helvetica", 8)
                c.drawString(60, y, description)
                y -= 20
            return y
        
        # [.. Dibujo de las 10 categorías ..]
        current_y = draw_category(current_y, "TITULO DE TIERRA URBANA- TITULO DE ADJUDICACION EN PROPIEDAD", "Una milésima de Bolívar, Art. 58 de la Ley Especial de Regularización", 'categoria1')
        current_y = draw_category(current_y, "TITULO DE TIERRA URBANA-TITULO DE ADJUDICACION MAS VIVIENDA", "Una milésima de Bolívar, más gastos administrativos(140 unidades ancladas a la moneda de mayor valor estipulada por el BCV)", 'categoria2')
        current_y = draw_category(current_y, "VIVIENDA UNIFAMILIAR Y MULTIFAMILIAR(EDIFICIOS) TIERRA: Municipal", "Precio: Gastos Administrativos(140 unidades ancladas a la moneda de mayor valor estipulada por el BCV)", 'categoria3')
        current_y = draw_category(current_y, "VIVIENDA UNIFAMILIAR Y MULTIFAMILIAR(EDIFICIOS) TIERRA: Tierra Privada", "Precio: Gastos Administrativos(140 unidades ancladas a la moneda de mayor valor estipulada por el BCV)", 'categoria4')
        current_y = draw_category(current_y, "VIVIENDA UNIFAMILIAR Y MULTIFAMILIAR(EDIFICIOS) TIERRA: Tierra INAVI o de cualquier Ente transferido al INTU", "Precio: Gastos Administrativos(140 unidades ancladas a la moneda de mayor valor estipulada por el BCV)", 'categoria5')
        current_y = draw_category(current_y, "EXCEDENTES: Con título de Tierra Urbana, hasta 400 mt2 una milésima por mt2", "Según el Art 33 de la Ley Especial de Regularización", 'categoria6')
        current_y = draw_category(current_y, "Con Título INAVI(Gastos Administrativos):", "140 unidades ancladas a la moneda de mayor valor estipulada por el BCV)", 'categoria7')
        current_y = draw_category(current_y, "ESTUDIOS TÉCNICO:", "Medición detallada de la parcela para obtener representación gráfica(plano)", 'categoria8')
        current_y = draw_category(current_y, "ARRENDAMIENTOS DE LOCALES COMERCIALES:", "Número de unidades establecidas en el contrato, ancladas a la moneda de mayor valor estipulada por el BCV", 'categoria9')
        current_y = draw_category(current_y, "ARRENDAMIENTOS DE TERRENOS", "Número de unidades establecidas en el contrato, ancladas a la moneda de mayor valor estipulada por el BCV", 'categoria10')
        
    current_y -= 70
    
    # === FIRMAS (Lógica de dibujo igual a la anterior) ===
    if current_y < 150:
        c.showPage()
        current_y = height - 100

    line_width = 200
    left_line_x = (width / 2 - line_width - 20)
    right_line_x = (width / 2 + 20)

    c.line(left_line_x, current_y, left_line_x + line_width, current_y)
    c.line(right_line_x, current_y, right_line_x + line_width, current_y)

    # Firma Izquierda (Cliente)
    c.setFont("Helvetica", 10)
    firma_text = "Firma"
    firma_width = c.stringWidth(firma_text, "Helvetica", 10)
    firma_x = left_line_x + (line_width - firma_width) / 2
    c.drawString(firma_x, current_y - 12, firma_text)

    current_y = draw_wrapped_name(c, nombre, left_line_x, current_y - 25, 
                                max_width=line_width, font_size=10, is_bold=True, line_height=12)

    c.setFont("Helvetica", 9)
    cedula_text = f"C.I./RIF: {cedula}"
    cedula_width = c.stringWidth(cedula_text, "Helvetica", 9)
    cedula_x = left_line_x + (line_width - cedula_width) / 2
    c.drawString(cedula_x, current_y - 4, cedula_text)

    current_y -= 35 
    
    # Firma Derecha (Recibido por)
    c.setFont("Helvetica", 10)
    recibido_text = "Recibido por:"
    recibido_width = c.stringWidth(recibido_text, "Helvetica", 10)
    recibido_x = right_line_x + (line_width - recibido_width) / 2
    c.drawString(recibido_x, current_y + 30, recibido_text)

    c.setFont("Helvetica-Bold", 10)
    instituto_text = "PRESLEY ORTEGA"
    instituto_width = c.stringWidth(instituto_text, "Helvetica-Bold", 10)
    instituto_x = right_line_x + (line_width - instituto_width) / 2
    c.drawString(instituto_x, current_y + 15, instituto_text)

    c.setFont("Helvetica", 10)
    cargo_text = "GERENTE DE ADMINISTRACIÓN Y SERVICIOS"
    cargo_width = c.stringWidth(cargo_text, "Helvetica", 10)
    cargo_x = right_line_x + (line_width - cargo_width) / 2
    c.drawString(cargo_x, current_y, cargo_text)

    # Finaliza el PDF y lo devuelve en el buffer
    c.save()
    buffer.seek(0)
    return buffer