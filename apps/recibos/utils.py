import pandas as pd
from django.db import transaction
from django.db.models import Max, Sum
from decimal import Decimal, InvalidOperation
from datetime import date
import logging
import re
import io
import os
from django.http import HttpResponse
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib.units import inch
from django.conf import settings
from unidecode import unidecode
from .constants import CATEGORY_CHOICES_MAP
from .models import Recibo

# I. FUNCIONES AUXILIARES (Conversión y Formato)

def to_boolean(value):
    """Convierte diversos tipos de entrada en valores booleanos."""
    TRUE_VALUES = {'sí', 'si', 'true', '1', 'x', 'y', True, 1}
    if pd.isna(value) or value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() in TRUE_VALUES
    return value in TRUE_VALUES

def limpiar_y_convertir_decimal(value):
    """Limpia strings de moneda y convierte a Decimal."""
    if pd.isna(value) or value is None:
        return Decimal(0)
    if isinstance(value, (int, float, Decimal)):
        try: return Decimal(value)
        except InvalidOperation: pass

    s = str(value).strip().lower()
    if not s or s in ['-', 'n/a', 'no aplica']:
        return Decimal(0)
    
    s_limpio = s.replace(' ', '').replace('$', '').replace('€', '')
    if ',' in s_limpio and '.' in s_limpio:
        s_limpio = s_limpio.replace('.', '').replace(',', '.')
    elif ',' in s_limpio:
        s_final = s_limpio.replace(',', '.')
    else:
        s_final = s_limpio

    if s_final.count('.') > 1:
        partes = s_final.rsplit('.', 1)
        s_final = partes[0].replace('.', '') + '.' + partes[1]

    try:
        return Decimal(s_final) if s_final else Decimal(0)
    except InvalidOperation:
        logging.getLogger('CH_RECIBOS').error(f"Error conversión Decimal: '{s_final}' (original: '{value}')")
        return Decimal(0)

def format_currency(amount):
    """Formatea montos a estilo contable (puntos para miles, coma para decimales)."""
    try:
        amount_decimal = Decimal(amount).quantize(Decimal('0.01'))
        formatted = "{:,.2f}".format(amount_decimal) 
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00"

# II. FUNCIÓN CLAVE: IMPORTACIÓN DE EXCEL
def importar_recibos_desde_excel(archivo_excel, usuario):
    """Procesa carga masiva desde Excel con validación de integridad."""
    log_rec = logging.getLogger('CH_RECIBOS')
    RIF_COL = 'rif_cedula_identidad'
    recibos_creados_pks = []
    
    COLUMNAS_CANONICAS = [
        'estado', 'nombre', RIF_COL, 'direccion_inmueble', 'ente_liquidado',
        'categoria1', 'categoria2', 'categoria3', 'categoria4', 'categoria5',
        'categoria6', 'categoria7', 'categoria8', 'categoria9', 'categoria10',
        'gastos_administrativos', 'tasa_dia', 'total_monto_bs',
        'numero_transferencia', 'conciliado', 'fecha', 'concepto'
    ]

    try:
        # 1. Lectura de hoja específica
        try:
            df = pd.read_excel(
                archivo_excel,
                sheet_name='Hoja2',
                header=3,
                dtype={'fecha': str, RIF_COL: str, 'numero_transferencia': str} 
            )
        except ValueError:
            return False, "Error de archivo: Asegúrate de que existe la hoja 'Hoja2'.", None

        df.dropna(how='all', inplace=True)
        if df.empty: return False, "El archivo Excel está vacío.", None

        df = df.iloc[:, :len(COLUMNAS_CANONICAS)]
        df.columns = COLUMNAS_CANONICAS
        
        # 2. Pre-procesamiento de datos
        df['fecha_procesada'] = pd.to_datetime(df['fecha'], errors='coerce', dayfirst=True).dt.date
        df = df.dropna(subset=['fecha_procesada']) 

        df['gastos_admin_proc'] = df['gastos_administrativos'].apply(limpiar_y_convertir_decimal)
        df['tasa_dia_proc'] = df['tasa_dia'].apply(limpiar_y_convertir_decimal)
        df['total_monto_proc'] = df['total_monto_bs'].apply(limpiar_y_convertir_decimal)
        
        for i in range(1, 11):
            df[f'categoria{i}'] = df[f'categoria{i}'].apply(to_boolean)
        df['conciliado'] = df['conciliado'].apply(to_boolean)
        
        # 3. Transacción Atómica
        with transaction.atomic():
            ultimo_recibo = Recibo.objects.aggregate(Max('numero_recibo'))['numero_recibo__max']
            consecutivo_actual = (ultimo_recibo or 0) + 1

            for index, fila_datos in df.iterrows():
                fila_numero = index + 5
                rif_cedula_raw = str(fila_datos.get(RIF_COL, '')).strip()
                nombre_raw = str(fila_datos.get('nombre', '')).strip()
                num_transf_raw = str(fila_datos.get('numero_transferencia', '')).strip().upper()
                
                # Validación de duplicados
                if num_transf_raw and num_transf_raw not in ['N/A', 'NAN', '']:
                    if Recibo.objects.filter(numero_transferencia=num_transf_raw).exists():
                        raise ValueError(f"Fila {fila_numero}: Transferencia '{num_transf_raw}' ya registrada.")

                if not rif_cedula_raw and not nombre_raw: continue
                if not rif_cedula_raw: raise ValueError(f"Fila {fila_numero}: RIF/Cédula es obligatorio.")
                
                data_a_insertar = {
                    'numero_recibo': consecutivo_actual,
                    'estado': unidecode(str(fila_datos.get('estado', '')).strip()).upper(),
                    'nombre': str(nombre_raw).title(),
                    'rif_cedula_identidad': str(rif_cedula_raw).strip().replace('.', '').replace('-', '').replace(' ', '').upper(),
                    'direccion_inmueble': str(fila_datos.get('direccion_inmueble', 'DIRECCION NO ESPECIFICADA')).strip().title(),
                    'ente_liquidado': str(fila_datos.get('ente_liquidado', 'ENTE NO ESPECIFICADO')).strip().title(),
                    'numero_transferencia': num_transf_raw if num_transf_raw not in ['NAN', ''] else None,
                    'concepto': str(fila_datos.get('concepto', '')).strip().title(),
                    'gastos_administrativos': fila_datos['gastos_admin_proc'],
                    'tasa_dia': fila_datos['tasa_dia_proc'],
                    'total_monto_bs': fila_datos['total_monto_proc'],
                    'fecha': fila_datos['fecha_procesada'],
                    'conciliado': fila_datos['conciliado'],
                    'usuario': usuario
                }
                
                for i in range(1, 11):
                    data_a_insertar[f'categoria{i}'] = fila_datos[f'categoria{i}']
                
                recibo_creado = Recibo.objects.create(**data_a_insertar)
                recibos_creados_pks.append(recibo_creado.pk)
                consecutivo_actual += 1

            return True, f"Importación masiva exitosa. Se generaron {len(recibos_creados_pks)} recibos.", recibos_creados_pks

    except ValueError as ve:
        return False, str(ve), None
    except Exception as e:
        log_rec.error(f"FALLO FATAL: {e}", exc_info=True)
        return False, "Fallo en la carga: Error desconocido en el procesamiento.", None


# III. GENERACIÓN DE REPORTES (Excel y PDF)

def generar_reporte_excel(request_filters, queryset, filtros_aplicados):
    """Genera un archivo Excel masivo con los recibos filtrados y hoja de resumen."""
    log_rec = logging.getLogger('CH_RECIBOS')
    data = []

    headers = [
        'Número Recibo', 'Nombre', 'Cédula/RIF', 'Fecha', 'Estado',
        'Monto Total (Bs.)', 'Tasa del Día', 'Gastos Administrativos', 
        'N° Transferencia', 'Concepto', 'Categorías'
    ]

    for recibo in queryset:
        categoria_detalle_nombres = [
            CATEGORY_CHOICES_MAP.get(f'categoria{i}', f'Categoría {i}')
            for i in range(1, 11) if getattr(recibo, f'categoria{i}')
        ]
        categorias_concatenadas = ','.join(categoria_detalle_nombres)

        row = [
            "{:04d}".format(recibo.numero_recibo), 
            recibo.nombre,
            recibo.rif_cedula_identidad,
            recibo.fecha.strftime('%Y-%m-%d'),
            recibo.estado,
            recibo.total_monto_bs, 
            recibo.tasa_dia, 
            recibo.gastos_administrativos, 
            recibo.numero_transferencia,
            recibo.concepto.strip() if recibo.concepto else "",
            categorias_concatenadas
        ]
        data.append(row)

    total_registros = queryset.count()
    total_monto_bs = queryset.aggregate(total=Sum('total_monto_bs'))['total'] or Decimal(0)
    
    # Resumen de filtros aplicados
    info_data = [
        ['Fecha de Generación', timezone.now().strftime('%Y-%m-%d %H:%M:%S')],
        ['Período del Reporte', filtros_aplicados.get('periodo', 'Todos los períodos')],
        ['Estado Filtrado', filtros_aplicados.get('estado', 'Todos los estados')],
        ['Categorías Filtradas', filtros_aplicados.get('categorias', 'Todas las categorías')],
        ['Total de Registros', total_registros],
        ['Monto Total (Bs)', total_monto_bs],
    ]
    info_df = pd.DataFrame(info_data, columns=['Parámetro', 'Valor'])
    df_recibos = pd.DataFrame(data, columns=headers)
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        info_df.to_excel(writer, index=False, sheet_name='info_reporte')
        df_recibos.to_excel(writer, index=False, sheet_name='Recibos', startrow=0, header=True)

        workbook = writer.book
        worksheet_recibos = writer.sheets['Recibos']

        # Formatos de celda
        money_format = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})
        tasa_format = workbook.add_format({'num_format': '#,##0.0000', 'align': 'right'}) 
        bold_format = workbook.add_format({'bold': True, 'bg_color': '#EAEAEA'})

        worksheet_recibos.set_column('A:A', 15)
        worksheet_recibos.set_column('B:C', 25)
        worksheet_recibos.set_column('D:D', 12)
        worksheet_recibos.set_column('E:E', 15)
        worksheet_recibos.set_column('F:F', 18, money_format) 
        worksheet_recibos.set_column('G:G', 18, tasa_format) 
        worksheet_recibos.set_column('H:H', 18, money_format) 
        worksheet_recibos.set_column('I:I', 20)
        worksheet_recibos.set_column('J:J', 40)
        worksheet_recibos.set_column('K:K', 50)

        for col_num, value in enumerate(headers):
            worksheet_recibos.write(0, col_num, value, bold_format)

        worksheet_info = writer.sheets['info_reporte']
        worksheet_info.set_column('A:A', 30)
        worksheet_info.set_column('B:B', 40)
        worksheet_info.write(0, 0, 'Parámetro', bold_format)
        worksheet_info.write(0, 1, 'Valor', bold_format)
        worksheet_info.write_number(5, 1, total_registros)
        worksheet_info.write_number(6, 1, total_monto_bs, money_format)
    
    output.seek(0)
    filename = f"Reporte_Recibos_Masivo_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment;filename="{filename}"'
    return response


# --- CONFIGURACIÓN DE RUTAS Y CONSTANTES DE PDF ---

try:
    HEADER_IMAGE = os.path.join(settings.BASE_DIR, 'apps', 'recibos', 'static', 'recibos', 'images', 'encabezado.png')
except AttributeError:
    HEADER_IMAGE = os.path.join(os.path.dirname(__file__), '..', 'static', 'recibos', 'images', 'encabezado.png')

CUSTOM_BLUE_DARK_TABLE = colors.HexColor("#427FBB")
CUSTOM_GREY_VERY_LIGHT = colors.HexColor("#F7F7F7")

# --- FUNCIONES AUXILIARES PARA EL PDF UNITARIO ---

def draw_text_line_unit(canvas_obj, text, x_start, y_start, font_name="Helvetica", font_size=10, is_bold=False):
    font = font_name + "-Bold" if is_bold else font_name
    canvas_obj.setFont(font, font_size)
    canvas_obj.drawString(x_start, y_start, str(text))
    return y_start - 15

def draw_centered_text_right_unit(canvas_obj, y_pos, text, x_start, width, font_name="Helvetica", font_size=10, is_bold=False):
    font = font_name + "-Bold" if is_bold else font_name
    canvas_obj.setFont(font, font_size)
    text_width = canvas_obj.stringWidth(text, font, font_size)
    x = x_start + (width - text_width) / 2
    canvas_obj.drawString(x, y_pos, text)

# MÓDULOS DE DIBUJO PARA PDF UNITARIO

def _draw_recibo_header(c, width, height):
    """Dibuja el encabezado gráfico y el título del documento."""
    log_rec = logging.getLogger('CH_RECIBOS')
    current_y = height - 50

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
            log_rec.error(f"⚠️ Error cargando encabezado PDF: {e}")

    c.setFont("Helvetica-Bold", 13)
    titulo_texto = "RECIBO DE PAGO"
    titulo_x = (width - c.stringWidth(titulo_texto, "Helvetica-Bold", 13)) / 2
    c.drawString(titulo_x, current_y, titulo_texto)
    return current_y - 25

def _draw_recibo_body_data(c, recibo_obj, y_start, X1_TITLE, X1_DATA, X2_TITLE, X2_DATA):
    """Renderiza el bloque de datos principales del contribuyente y pago."""
    num_recibo = str(recibo_obj.numero_recibo).zfill(9) if recibo_obj.numero_recibo else 'N/A'
    monto_formateado = format_currency(recibo_obj.total_monto_bs)
    fecha_str = recibo_obj.fecha.strftime("%d/%m/%Y")
    num_transf = recibo_obj.numero_transferencia if recibo_obj.numero_transferencia else 'N/A'

    styles = getSampleStyleSheet()
    style_dato = ParagraphStyle('DatoStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=9, alignment=TA_LEFT)
    
    ancho_col1 = X2_TITLE - X1_DATA - 10 
    ancho_col2 = 550 - X2_DATA

    def dibujar_campo(canvas, label, texto, x_label, x_dato, y, ancho_max):
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(x_label, y, label)
        p = Paragraph(str(texto), style_dato)
        w, h = p.wrap(ancho_max, 100) 
        p.drawOn(canvas, x_dato, y - h + 7) 
        return h 

    y_line = y_start
    h1 = dibujar_campo(c, "Estado:", recibo_obj.estado, X1_TITLE, X1_DATA, y_line, ancho_col1)
    h2 = dibujar_campo(c, "Nº Recibo:", num_recibo, X2_TITLE, X2_DATA, y_line, ancho_col2)
    y_line -= max(h1, h2, 15) + 5

    h1 = dibujar_campo(c, "Recibí de:", recibo_obj.nombre, X1_TITLE, X1_DATA, y_line, ancho_col1)
    h2 = dibujar_campo(c, "Monto Recibido (Bs.):", monto_formateado, X2_TITLE, X2_DATA, y_line, ancho_col2)
    y_line -= max(h1, h2, 15) + 5

    h1 = dibujar_campo(c, "Rif/C.I:", recibo_obj.rif_cedula_identidad, X1_TITLE, X1_DATA, y_line, ancho_col1)
    h2 = dibujar_campo(c, "Nº Transferencia:", num_transf, X2_TITLE, X2_DATA, y_line, ancho_col2)
    y_line -= max(h1, h2, 15) + 5

    h1 = dibujar_campo(c, "Dirección:", recibo_obj.direccion_inmueble, X1_TITLE, X1_DATA, y_line, ancho_col1)
    h2 = dibujar_campo(c, "Fecha:", fecha_str, X2_TITLE, X2_DATA, y_line, ancho_col2)
    y_line -= max(h1, h2, 15) + 5

    h_concepto = dibujar_campo(c, "Concepto:", recibo_obj.concepto, X1_TITLE, X1_DATA, y_line, 550 - X1_DATA)
    return y_line - h_concepto - 20

def _draw_categorias_section(c, recibo_obj, y_start, X1_TITLE):
    """Dibuja la sección descriptiva de las categorías de regularización."""
    styles = getSampleStyleSheet()
    style_titulo_cat = ParagraphStyle('CatTitulo', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=9)
    style_detalle_cat = ParagraphStyle('CatDetalle', parent=styles['Normal'], fontName='Helvetica', fontSize=7, leading=9, leftIndent=10)

    categorias = {f'categoria{i}': getattr(recibo_obj, f'categoria{i}') for i in range(1, 11)}
    current_y = y_start

    if any(categorias.values()):
        c.setFont("Helvetica-Bold", 10)
        c.drawString(X1_TITLE, current_y, "FORMA DE PAGO Y DESCRIPCIÓN DE LA REGULARIZACIÓN")
        current_y -= 20

        CATEGORY_DESCRIPTIONS = {
            'categoria1': ("TITULO DE TIERRA URBANA - TITULO DE ADJUDICACION EN PROPIEDAD", "Una milésima de Bolívar, Art. 58 de la Ley Especial de Regularización"),
            'categoria2': ("TITULO DE TIERRA URBANA - TITULO DE ADJUDICACION MAS VIVIENDA", "Una milésima de Bolívar, más gastos administrativos (140 unidades BCV)"),
            'categoria3': ("VIVIENDA UNIFAMILIAR Y MULTIFAMILIAR (EDIFICIOS) TIERRA: Municipal", "Precio: Gastos Administrativos (140 unidades BCV)"),
            'categoria4': ("VIVIENDA UNIFAMILIAR Y MULTIFAMILIAR (EDIFICIOS) TIERRA: Tierra Privada", "Precio: Gastos Administrativos (140 unidades BCV)"),
            'categoria5': ("VIVIENDA UNIFAMILIAR Y MULTIFAMILIAR (EDIFICIOS) TIERRA: Tierra INAVI/INTU", "Precio: Gastos Administrativos (140 unidades BCV)"),
            'categoria6': ("EXCEDENTES: Tierra Urbana hasta 400 mt2", "Según el Art 33 de la Ley Especial de Regularización"),
            'categoria7': ("Con Título INAVI (Gastos Administrativos):", "140 unidades ancladas a la moneda de mayor valor BCV"),
            'categoria8': ("ESTUDIOS TÉCNICOS:", "Medición detallada de la parcela para plano"),
            'categoria9': ("ARRENDAMIENTOS DE LOCALES COMERCIALES:", "Unidades establecidas en contrato (BCV)"),
            'categoria10': ("ARRENDAMIENTOS DE TERRENOS", "Unidades establecidas en contrato (BCV)"),
        }
        
        ancho_disponible = 450 

        for key, (title, detail) in CATEGORY_DESCRIPTIONS.items():
            if categorias.get(key, False):
                p_title = Paragraph(title.replace(":", ":<br/>"), style_titulo_cat)
                w_t, h_t = p_title.wrap(ancho_disponible, 100)
                
                if current_y - h_t < 100:
                    c.showPage()
                    current_y = 750 

                p_title.drawOn(c, X1_TITLE, current_y - h_t)
                c.setFont("Helvetica-Bold", 10)
                c.drawString(520, current_y - 8, "X")
                current_y -= (h_t + 2)

                p_detail = Paragraph(detail, style_detalle_cat)
                w_d, h_d = p_detail.wrap(ancho_disponible - 10, 100)
                
                if current_y - h_d < 50:
                    c.showPage()
                    current_y = 750

                p_detail.drawOn(c, X1_TITLE, current_y - h_d)
                current_y -= (h_d + 10)

    return current_y - 70

# --- SECCIÓN DE FIRMAS Y FINALIZACIÓN DE PDF ---

def _draw_signatures_section(c, recibo_obj, y_start, width):
    """Dibuja la sección de firmas con soporte para nombres largos y cargos legales."""
    current_y = y_start
    line_width = 180
    left_line_x = (width / 4) - (line_width / 2)
    right_line_x = (3 * width / 4) - (line_width / 2)

    c.setLineWidth(1)
    c.line(left_line_x, current_y, left_line_x + line_width, current_y)
    c.line(right_line_x, current_y, right_line_x + line_width, current_y)

    # --- FIRMA CLIENTE (IZQUIERDA) ---
    y_sig = current_y - 12
    draw_centered_text_right_unit(c, y_sig, "Firma", left_line_x, line_width, font_size=8)
    
    styles = getSampleStyleSheet()
    nombre_style = ParagraphStyle('NombreStyle', fontName='Helvetica-Bold', fontSize=9, leading=10, alignment=TA_CENTER)
    
    p_nombre = Paragraph(recibo_obj.nombre.upper(), nombre_style)
    w_p, h_p = p_nombre.wrap(line_width, 100) 
    y_pos_nombre = y_sig - h_p - 5 
    p_nombre.drawOn(c, left_line_x, y_pos_nombre)
    
    y_rif = y_pos_nombre - 12 
    draw_centered_text_right_unit(c, y_rif, f"C.I./RIF: {recibo_obj.rif_cedula_identidad}", left_line_x, line_width, font_size=8)

    # --- FIRMA INSTITUCIÓN (DERECHA) ---
    y_sig_inst = current_y - 12
    draw_centered_text_right_unit(c, y_sig_inst, "Recibido por:", right_line_x, line_width, font_size=8)
    
    y_sig_inst -= 14
    draw_centered_text_right_unit(c, y_sig_inst, "PRESLEY ORTEGA", right_line_x, line_width, is_bold=True, font_size=9)
    
    y_sig_inst -= 12
    draw_centered_text_right_unit(c, y_sig_inst, "GERENTE DE ADMINISTRACIÓN Y SERVICIOS", right_line_x, line_width, is_bold=False, font_size=9)
    
    y_sig_inst -= 14
    textos_legales = [
        "Designado según Gaceta Oficial N° 43.062,",
        "de fecha 16 de febrero de 2025 y",
        "Providencia N° 016-2024 de fecha",
        "16 de diciembre de 2024"
    ]
    
    for linea in textos_legales:
        draw_centered_text_right_unit(c, y_sig_inst, linea, right_line_x, line_width, font_size=7)
        y_sig_inst -= 9

    return current_y

# FUNCIÓN PRINCIPAL DE PDF UNITARIO
def generar_pdf_recibo_unitario(recibo_obj):
    """Crea el PDF individual de un recibo con todas sus secciones."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Márgenes y coordenadas base
    X1_TITLE, X1_DATA = 60, 160
    X2_TITLE, X2_DATA = 310, 470
    
    current_y = _draw_recibo_header(c, width, height)
    current_y = _draw_recibo_body_data(c, recibo_obj, current_y, X1_TITLE, X1_DATA, X2_TITLE, X2_DATA)
    
    if current_y < 350: 
        logging.getLogger('CH_RECIBOS').warning("Espacio reducido para categorías en PDF unitario.")
        
    current_y = _draw_categorias_section(c, recibo_obj, current_y, X1_TITLE)
    
    if current_y < 150:
        c.showPage()
        current_y = height - 100
    
    _draw_signatures_section(c, recibo_obj, current_y, width)

    c.showPage()
    c.save()
    buffer.seek(0)
    
    num_recibo = str(recibo_obj.numero_recibo).zfill(9) if recibo_obj.numero_recibo else 'N_A'
    filename = f"Recibo_N_{num_recibo}_{recibo_obj.rif_cedula_identidad}.pdf"
    
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

# FUNCIÓN PRINCIPAL DE PDF REPORTE MASIVO

def draw_report_logo_and_page_number(canvas, doc):
    """Callback para dibujar encabezados y pies de página en reportes masivos."""
    log_rec = logging.getLogger('CH_RECIBOS')
    canvas.saveState()
    width, height = doc.pagesize
    page_number = canvas.getPageNumber()

    if page_number == 1 and os.path.exists(HEADER_IMAGE):
        try:
            img = ImageReader(HEADER_IMAGE)
            img_width, img_height = img.getSize()
            scale = min(1.0, 700 / img_width)
            draw_width, draw_height = img_width * scale, img_height * scale
            canvas.drawImage(HEADER_IMAGE, x=(width - draw_width) / 2, y=height - draw_height - 10, width=draw_width, height=draw_height)
        except Exception as e:
            log_rec.error(f"Error dibujando encabezado en reporte PDF: {e}")

    canvas.setFont('Helvetica', 8)
    canvas.drawString(width - 70, 30, f"Página {page_number}")
    canvas.drawString(36, 30, f"Reporte generado el: {timezone.now().strftime('%d/%m/%Y %H:%M')}")
    canvas.restoreState()

def generar_pdf_reporte(queryset, filtros_aplicados):
    """Genera un reporte tabular en PDF (paisaje) de los recibos filtrados."""
    def formatear_celda(texto, max_chars, estilo):
        if not texto: return Paragraph('', estilo)
        texto = str(texto).strip()
        if max_chars and len(texto) > max_chars:
            texto = texto[:max_chars] + "..."
        return Paragraph(texto, estilo)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), leftMargin=30, rightMargin=30, topMargin=110, bottomMargin=40)

    Story = []
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='CenteredTitle', alignment=TA_CENTER, fontSize=16, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='FilterTextLeft', alignment=TA_LEFT, fontSize=9, leading=12))
    styles.add(ParagraphStyle(name='CustomCellStyle', fontSize=8, leading=10, wordWrap='LTR'))
    styles.add(ParagraphStyle(name='AmountCellStyle', fontSize=8, leading=10, alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name='ResumenTitleLeft', alignment=TA_LEFT, fontSize=11, fontName='Helvetica-Bold', spaceBefore=5))

    total_registros = queryset.count()
    total_monto_bs = queryset.aggregate(total=Sum('total_monto_bs'))['total'] or Decimal(0)

    Story.append(Paragraph("REPORTE DE RECIBOS DE PAGO", styles['CenteredTitle']))
    Story.append(Spacer(1, 10))

    filtros_linea = f"<b>Período:</b> {filtros_aplicados.get('periodo', 'Todos')} | <b>Estado:</b> {filtros_aplicados.get('estado', 'Todos')} | <b>Categorías:</b> {filtros_aplicados.get('categorias', 'Todas')}"
    Story.append(Paragraph(filtros_linea, styles['FilterTextLeft']))
    Story.append(Spacer(1, 8))

    table_data = [['Recibo', 'Nombre', 'Cédula/RIF', 'Monto (Bs)', 'Fecha', 'Estado', 'Transferencia', 'Concepto']]
    col_widths = [0.6*inch, 2.1*inch, 1.1*inch, 1.0*inch, 0.8*inch, 0.9*inch, 1.6*inch, 2.1*inch]

    for recibo in queryset:
        table_data.append([
            "{:04d}".format(recibo.numero_recibo) if recibo.numero_recibo else '', 
            formatear_celda(recibo.nombre, 60, styles['CustomCellStyle']),
            formatear_celda(recibo.rif_cedula_identidad, None, styles['CustomCellStyle']), 
            formatear_celda(format_currency(recibo.total_monto_bs), None, styles['AmountCellStyle']), 
            recibo.fecha.strftime('%d/%m/%Y'),
            formatear_celda(recibo.estado, 15, styles['CustomCellStyle']),
            formatear_celda(recibo.numero_transferencia, 40, styles['CustomCellStyle']),
            formatear_celda(recibo.concepto, 70, styles['CustomCellStyle']) 
        ])

    table = Table(table_data, colWidths=col_widths, repeatRows=1) 
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), CUSTOM_BLUE_DARK_TABLE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, CUSTOM_GREY_VERY_LIGHT]),
    ]))

    Story.append(table)
    Story.append(Spacer(1, 20))
    Story.append(Paragraph("RESUMEN DEL REPORTE:", styles['ResumenTitleLeft']))
    Story.append(Paragraph(f"<b>Total de Recibos:</b> {total_registros}", styles['FilterTextLeft']))
    Story.append(Paragraph(f"<b>Monto Total Bs:</b> {format_currency(total_monto_bs)}", styles['FilterTextLeft']))

    doc.build(Story, onFirstPage=draw_report_logo_and_page_number, onLaterPages=draw_report_logo_and_page_number)
    buffer.seek(0)
    filename = f"Reporte_Recibos_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment;filename="{filename}"'
    return response