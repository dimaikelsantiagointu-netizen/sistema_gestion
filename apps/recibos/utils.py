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

logger = logging.getLogger(__name__)

# I. FUNCIONES AUXILIARES DE DATOS (Decimales y Booleanos)

def to_boolean(value):

    TRUE_VALUES = {'sí', 'si', 'true', '1', 'x', 'y', True, 1}
    
    if pd.isna(value) or value is None:
        return False
    
    if isinstance(value, str):
        return value.strip().lower() in TRUE_VALUES
    if isinstance(value, (int, bool)):
        return value in TRUE_VALUES
        
    return False


def limpiar_y_convertir_decimal(value):

    if pd.isna(value) or value is None:
        return Decimal(0)

    if isinstance(value, (int, float, Decimal)):
        try:
            return Decimal(value)
        except InvalidOperation:
            pass

    s = str(value).strip().lower()
    
    if not s or s in ['-', 'n/a', 'no aplica']:
        return Decimal(0)
    
    s_limpio = s.replace(' ', '').replace('$', '').replace('€', '')
    
    if ',' in s_limpio and '.' in s_limpio:
        s_limpio = s_limpio.replace('.', '')
        s_final = s_limpio.replace(',', '.')
    elif ',' in s_limpio:
        s_final = s_limpio.replace(',', '.')
    else:
        s_final = s_limpio

    if s_final.count('.') > 1:
        partes = s_final.rsplit('.', 1)
        s_final = partes[0].replace('.', '') + '.' + partes[1]

    try:
        if not s_final:
            return Decimal(0)
        return Decimal(s_final)
    except InvalidOperation:
        logger.error(f"Error conversión Decimal: '{s_final}' (original: '{value}')")
        return Decimal(0)


def format_currency(amount):

    try:
        amount_decimal = Decimal(amount).quantize(Decimal('0.01'))
        formatted = "{:,.2f}".format(amount_decimal) 
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted
    except Exception:
        return "0,00"

# II. FUNCIÓN CLAVE: IMPORTACIÓN DE EXCEL

def importar_recibos_desde_excel(archivo_excel, usuario):
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
        # 1. LECTURA Y VALIDACIÓN INICIAL DE EXCEL
        try:
            df = pd.read_excel(
                archivo_excel,
                sheet_name='Hoja2',
                header=3,
                dtype={'fecha': str, RIF_COL: str, 'numero_transferencia': str} 
            )
        except ValueError as e:
            return False, "Error de archivo: Asegúrate de que existe la hoja 'Hoja2' y el formato es válido.", None

        df.dropna(how='all', inplace=True)

        if df.empty:
            return False, "El archivo Excel está vacío o la hoja 'Hoja2' no contiene datos válidos.", None

        if df.shape[1] < len(COLUMNAS_CANONICAS):
            return False, f"Error: Se encontraron {df.shape[1]} columnas, se esperaban {len(COLUMNAS_CANONICAS)}. Revise el encabezado (Fila 4).", None

        df = df.iloc[:, :len(COLUMNAS_CANONICAS)]
        df.columns = COLUMNAS_CANONICAS
        
        # 2. PRE-PROCESAMIENTO DE DATOS EN DATAFRAME
        
        df['fecha_procesada'] = pd.to_datetime(df['fecha'], errors='coerce', dayfirst=True).dt.date
        
        df = df.dropna(subset=['fecha_procesada']) 

        df['gastos_admin_proc'] = df['gastos_administrativos'].apply(limpiar_y_convertir_decimal)
        df['tasa_dia_proc'] = df['tasa_dia'].apply(limpiar_y_convertir_decimal)
        df['total_monto_proc'] = df['total_monto_bs'].apply(limpiar_y_convertir_decimal)
        
        for i in range(1, 11):
            key = f'categoria{i}'
            df[key] = df[key].apply(to_boolean)
        df['conciliado'] = df['conciliado'].apply(to_boolean)
        
        with transaction.atomic():
            ultimo_recibo = Recibo.objects.aggregate(Max('numero_recibo'))['numero_recibo__max']
            consecutivo_actual = (ultimo_recibo or 0) + 1

            for index, fila_datos in df.iterrows():
                
                fila_numero = index + 5
                
                rif_cedula_raw = str(fila_datos.get(RIF_COL, '')).strip()
                nombre_raw = str(fila_datos.get('nombre', '')).strip()

                if not rif_cedula_raw and not nombre_raw:
                    logger.warning(f"Fila {fila_numero}: Saltada por no tener RIF/Cédula ni Nombre.")
                    continue
                if not rif_cedula_raw:
                    # RIF/Cédula es obligatorio
                    raise ValueError(f"Fila {fila_numero}: El campo RIF/Cédula es obligatorio y está vacío.")
                
                # Construcción del diccionario de datos (usa los campos pre-procesados)
                data_a_insertar = {
                    'numero_recibo': consecutivo_actual,
                    'estado': unidecode(str(fila_datos.get('estado', '')).strip()).upper(),
                    'nombre': str(nombre_raw).title(),
                    'rif_cedula_identidad': str(rif_cedula_raw).strip().replace('.', '').replace('-', '').replace(' ', '').upper(),
                    'direccion_inmueble': str(fila_datos.get('direccion_inmueble', 'DIRECCION NO ESPECIFICADA')).strip().title(),
                    'ente_liquidado': str(fila_datos.get('ente_liquidado', 'ENTE NO ESPECIFICADO')).strip().title(),
                    'numero_transferencia': str(fila_datos.get('numero_transferencia', '')).strip().upper(),
                    'concepto': str(fila_datos.get('concepto', '')).strip().title(),
                    
                    'gastos_administrativos': fila_datos['gastos_admin_proc'],
                    'tasa_dia': fila_datos['tasa_dia_proc'],
                    'total_monto_bs': fila_datos['total_monto_proc'],
                    
                    'fecha': fila_datos['fecha_procesada'],
                    'conciliado': fila_datos['conciliado'],
                    'usuario': usuario
                }
                
                for i in range(1, 11):
                    key = f'categoria{i}'
                    data_a_insertar[key] = fila_datos[key]
                
                recibo_creado = Recibo.objects.create(**data_a_insertar)
                recibos_creados_pks.append(recibo_creado.pk)
                consecutivo_actual += 1
                logger.info(f"ÉXITO: Recibo N°{recibo_creado.numero_recibo} generado para {data_a_insertar['nombre']} (Fila {fila_numero}).")


            if recibos_creados_pks:
                total_creados = len(recibos_creados_pks)
                primer_num = str(consecutivo_actual - total_creados).zfill(4)
                ultimo_num = str(consecutivo_actual - 1).zfill(4)
                mensaje = f"Importación masiva exitosa. Se generaron {total_creados} recibos, desde N°{primer_num} hasta N°{ultimo_num}."
                return True, mensaje, recibos_creados_pks
            else:
                mensaje = "Importación terminada. No se encontraron registros válidos para crear recibos (todas las filas vacías, sin RIF, o con fecha inválida)."
                return True, mensaje, []

    except Exception as e:
        error_message = f"FALLO FATAL DE CARGA: {e}"
        logger.error(error_message, exc_info=True)
        if "Fila " in str(e):
             return False, str(e), None
        return False, f"Fallo en la carga de Excel: Error desconocido.", None


# III. GENERACIÓN DE REPORTES (Excel y PDF)

def generar_reporte_excel(request_filters, queryset, filtros_aplicados):
    
    data = []

    headers = [
        'Número Recibo',
        'Nombre',
        'Cédula/RIF',
        'Fecha',
        'Estado',
        'Monto Total (Bs.)',
        'Tasa del Día', 
        'Gastos Administrativos', 
        'N° Transferencia',
        'Concepto',
        'Categorías'
    ]

    for recibo in queryset:
        categoria_detalle_nombres = [
            CATEGORY_CHOICES_MAP.get(f'categoria{i}', f'Categoría {i} (Desconocida)')
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
            recibo.concepto.strip(),
            categorias_concatenadas
        ]
        data.append(row)

    total_registros = queryset.count()
    total_monto_bs = queryset.aggregate(total=Sum('total_monto_bs'))['total'] or Decimal(0)
    
    # Datos de la hoja 'info_reporte'
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

        # Formatos de Excel para datos numéricos
        money_format = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})
        tasa_format = workbook.add_format({'num_format': '#,##0.0000', 'align': 'right'}) 
        bold_format = workbook.add_format({'bold': True, 'bg_color': '#EAEAEA'})

        # Ajuste de ancho de columnas y aplicación de formatos
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

        # 1. Aplicamos el formato negrita a los encabezados
        worksheet_info.write(0, 0, 'Parámetro', bold_format)
        worksheet_info.write(0, 1, 'Valor', bold_format)
        
        # 2. Re-escribimos los valores numéricos con el formato correcto 
        # para que no se vean como texto o con formatos cruzados.
        
        # El índice 4 de tu info_data (Total Registros) está en la FILA 5 de Excel 
        # (porque la fila 0 es el encabezado)
        worksheet_info.write_number(5, 1, total_registros)
        
        # El índice 5 de tu info_data (Monto Total) está en la FILA 6 de Excel
        worksheet_info.write_number(6, 1, total_monto_bs, money_format)
    
    output.seek(0)

    filename = f"Reporte_Recibos_Masivo_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment;filename="{filename}"'
    return response


# --- CONFIGURACIÓN DE RUTAS Y CONSTANTES DE PDF ---

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


CUSTOM_BLUE_DARK_TABLE = colors.HexColor("#427FBB")
CUSTOM_GREY_VERY_LIGHT = colors.HexColor("#F7F7F7")

# --- FUNCIONES AUXILIARES PARA EL PDF UNITARIO 

def draw_text_line_unit(canvas_obj, text, x_start, y_start, font_name="Helvetica", font_size=10, is_bold=False):
    """Dibuja una línea de texto y ajusta la posición Y."""
    font = font_name + "-Bold" if is_bold else font_name
    canvas_obj.setFont(font, font_size)
    canvas_obj.drawString(x_start, y_start, str(text))
    return y_start - 15

def draw_centered_text_right_unit(canvas_obj, y_pos, text, x_start, width, font_name="Helvetica", font_size=10, is_bold=False):
    """Centra el texto dentro de un ancho específico."""
    font = font_name + "-Bold" if is_bold else font_name
    canvas_obj.setFont(font, font_size)
    text_width = canvas_obj.stringWidth(text, font, font_size)
    x = x_start + (width - text_width) / 2
    canvas_obj.drawString(x, y_pos, text.upper())

# ⚙️ MÓDULOS DE DIBUJO PARA PDF UNITARIO (Para una función generar_pdf_recibo_unitario más limpia)

def _draw_recibo_header(c, width, height):
    """Dibuja el encabezado y el título del recibo unitario."""
    current_y = height - 50
    y_top = height - 50

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
    
    return current_y

def _draw_recibo_body_data(c, recibo_obj, y_start, X1_TITLE, X1_DATA, X2_TITLE, X2_DATA):
    """Dibuja los datos principales del recibo (Estado, Nombre, Monto, etc.)."""
    
    num_recibo = str(recibo_obj.numero_recibo).zfill(4) if recibo_obj.numero_recibo else 'N/A'
    monto_formateado = format_currency(recibo_obj.total_monto_bs)
    fecha_str = recibo_obj.fecha.strftime("%d/%m/%Y")
    num_transf = recibo_obj.numero_transferencia if recibo_obj.numero_transferencia else 'N/A'
    
    y_line = y_start

    # --- FILA 1: Estado / Nº Recibo ---
    # Dibujar Títulos. draw_text_line_unit DECREMENTA y_line
    y_line = draw_text_line_unit(c, "Estado:", X1_TITLE, y_line, is_bold=True)
    
    # Dibujar Datos. 
    draw_text_line_unit(c, recibo_obj.estado, X1_DATA, y_line + 15, is_bold=False)
    
    # Dibujar Título Columna 2.
    draw_text_line_unit(c, "Nº Recibo:", X2_TITLE, y_line + 15, is_bold=True)
    
    # Dibujar Dato Columna 2.
    draw_text_line_unit(c, num_recibo, X2_DATA, y_line + 15, is_bold=False)
    y_line -= 5 

    # --- FILA 2: Recibí de / Monto Recibido (Bs.) ---
    y_line = draw_text_line_unit(c, "Recibí de:", X1_TITLE, y_line, is_bold=True)
    draw_text_line_unit(c, recibo_obj.nombre, X1_DATA, y_line + 15, is_bold=False)
    draw_text_line_unit(c, "Monto Recibido (Bs.):", X2_TITLE, y_line + 15, is_bold=True)
    draw_text_line_unit(c, monto_formateado, X2_DATA, y_line + 15, is_bold=False)
    y_line -= 5

    # --- FILA 3: Rif/C.I / Nº Transferencia ---
    y_line = draw_text_line_unit(c, "Rif/C.I:", X1_TITLE, y_line, is_bold=True)
    draw_text_line_unit(c, recibo_obj.rif_cedula_identidad, X1_DATA, y_line + 15, is_bold=False)
    draw_text_line_unit(c, "Nº Transferencia:", X2_TITLE, y_line + 15, is_bold=True)
    draw_text_line_unit(c, num_transf, X2_DATA, y_line + 15, is_bold=False)
    y_line -= 5

    # --- FILA 4: Dirección / Fecha ---
    y_line = draw_text_line_unit(c, "Dirección:", X1_TITLE, y_line, is_bold=True)
    draw_text_line_unit(c, recibo_obj.direccion_inmueble, X1_DATA, y_line + 15, is_bold=False)
    draw_text_line_unit(c, "Fecha:", X2_TITLE, y_line + 15, is_bold=True)
    draw_text_line_unit(c, fecha_str, X2_DATA, y_line + 15, is_bold=False)
    y_line -= 5

    # --- FILA 5: Concepto ---
    y_line = draw_text_line_unit(c, "Concepto:", X1_TITLE, y_line, is_bold=True)
    draw_text_line_unit(c, recibo_obj.concepto, X1_DATA, y_line + 15, is_bold=False)
    
    return y_line - 25

def _draw_categorias_section(c, recibo_obj, y_start, X1_TITLE):
    """Dibuja la sección de categorías detalladas en el recibo unitario."""
    
    categorias = {
        f'categoria{i}': getattr(recibo_obj, f'categoria{i}') for i in range(1, 11)
    }
    hay_categorias = any(categorias.values())
    current_y = y_start

    if hay_categorias:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(X1_TITLE, current_y, "FORMA DE PAGO Y DESCRIPCION DE LA REGULARIZACION")
        current_y -= 25

        # Diccionario auxiliar para simplificar la lógica repetitiva
        CATEGORY_DESCRIPTIONS = {
            'categoria1': ("TITULO DE TIERRA URBANA - TITULO DE ADJUDICACION EN PROPIEDAD", "Una milésima de Bolívar, Art. 58 de la Ley Especial de Regularización"),
            'categoria2': ("TITULO DE TIERRA URBANA - TITULO DE ADJUDICACION MAS VIVIENDA", "Una milésima de Bolívar, más gastos administrativos (140 unidades ancladas a la moneda de mayor valor estipulada por el BCV)"),
            'categoria3': ("VIVIENDA UNIFAMILIAR Y MULTIFAMILIAR (EDIFICIOS) TIERRA: Municipal", "Precio: Gastos Administrativos (140 unidades ancladas a la moneda de mayor valor estipulada por el BCV)"),
            'categoria4': ("VIVIENDA UNIFAMILIAR Y MULTIFAMILIAR (EDIFICIOS) TIERRA: Tierra Privada", "Precio: Gastos Administrativos (140 unidades ancladas a la moneda de mayor valor estipulada por el BCV)"),
            'categoria5': ("VIVIENDA UNIFAMILIAR Y MULTIFAMILIAR (EDIFICIOS) TIERRA: Tierra INAVI o de cualquier Ente transferido al INTU", "Precio: Gastos Administrativos (140 unidades ancladas a la moneda de mayor valor estipulada por el BCV)"),
            'categoria6': ("EXCEDENTES: Con título de Tierra Urbana, hasta 400 mt2 una milésima por mt2", "Según el Art 33 de la Ley Especial de Regularización"),
            'categoria7': ("Con Título INAVI (Gastos Administrativos):", "140 unidades ancladas a la moneda de mayor valor estipulada por el BCV)"),
            'categoria8': ("ESTUDIOS TÉCNICOS:", "Medición detallada de la parcela para obtener representación gráfica (plano)"),
            'categoria9': ("ARRENDAMIENTOS DE LOCALES COMERCIALES:", "Número de unidades establecidas en el contrato, ancladas a la moneda de mayor valor estipulada por el BCV"),
            'categoria10': ("ARRENDAMIENTOS DE TERRENOS", "Número de unidades establecidas en el contrato, ancladas a la moneda de mayor valor estipulada por el BCV"),
        }
        
        for key, (title, detail) in CATEGORY_DESCRIPTIONS.items():
            if categorias.get(key, False):
                current_y = draw_text_line_unit(c, title, X1_TITLE, current_y, font_size=9, is_bold=True)
                c.drawString(520, current_y + 15, "X")
                current_y = draw_text_line_unit(c, detail, X1_TITLE, current_y, font_size=8, is_bold=False)
                current_y -= 5

    return current_y - 70

def _draw_signatures_section(c, recibo_obj, y_start, width):
    """Dibuja la sección de firmas del recibo unitario."""
    current_y = y_start
    line_width = 200
    left_line_x = (width / 2 - line_width - 20)
    right_line_x = (width / 2 + 20)

    # LÍNEAS DE FIRMA
    c.line(left_line_x, current_y, left_line_x + line_width, current_y)
    c.line(right_line_x, current_y, right_line_x + line_width, current_y)

    # FIRMA CLIENTE
    y_sig = current_y - 15
    draw_centered_text_right_unit(c, y_sig, "Firma", left_line_x, line_width)
    y_sig -= 13
    draw_centered_text_right_unit(c, y_sig, recibo_obj.nombre, left_line_x, line_width, is_bold=True)
    y_sig -= 12
    draw_centered_text_right_unit(c, y_sig, f"C.I./RIF: {recibo_obj.rif_cedula_identidad}", left_line_x, line_width, font_size=9)

    # FIRMA INSTITUCIÓN
    y_sig_inst = current_y - 15
    draw_centered_text_right_unit(c, y_sig_inst, "Recibido por:", right_line_x, line_width)
    y_sig_inst -= 13
    draw_centered_text_right_unit(c, y_sig_inst, "PRESLEY ORTEGA", right_line_x, line_width, is_bold=True)
    y_sig_inst -= 12
    draw_centered_text_right_unit(c, y_sig_inst, "GERENTE DE ADMINISTRACIÓN Y SERVICIOS", right_line_x, line_width, font_size=9)
    y_sig_inst -= 15
    draw_centered_text_right_unit(c, y_sig_inst, "Designado según gaceta oficial n°43.062 de fecha", right_line_x, line_width, font_size=8)
    y_sig_inst -= 10
    draw_centered_text_right_unit(c, y_sig_inst, "16 de febrero de 2025 y Providencia de", right_line_x, line_width, font_size=8)
    y_sig_inst -= 10
    draw_centered_text_right_unit(c, y_sig_inst, "n°016-2024 de fecha 16 de diciembre de 2024", right_line_x, line_width, font_size=8)


# FUNCIÓN PRINCIPAL DE PDF UNITARIO
def generar_pdf_recibo_unitario(recibo_obj):
    """
    Genera el contenido del PDF individual para un recibo de forma modular.
    Retorna directamente el HttpResponse para forzar la descarga.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Coordenadas
    X1_TITLE = 60
    X1_DATA = 160
    X2_TITLE = 310
    X2_DATA = 470
    
    # 1. Dibujar Encabezado
    current_y = _draw_recibo_header(c, width, height)
    
    # 2. Dibujar Datos del Cuerpo
    current_y = _draw_recibo_body_data(c, recibo_obj, current_y, X1_TITLE, X1_DATA, X2_TITLE, X2_DATA)
    
    # 3. Dibujar Categorías
    if current_y < 350: 
        logger.warning("Poco espacio disponible para dibujar la sección de categorías.")
        
    current_y = _draw_categorias_section(c, recibo_obj, current_y, X1_TITLE)
    
    # 4. Dibujar Firmas
    if current_y < 150:
        c.showPage()
        current_y = height - 100
    
    _draw_signatures_section(c, recibo_obj, current_y, width)

    c.showPage()
    c.save()
    buffer.seek(0)
    
    num_recibo = str(recibo_obj.numero_recibo).zfill(4) if recibo_obj.numero_recibo else 'N_A'
    filename = f"Recibo_N_{num_recibo}_{recibo_obj.rif_cedula_identidad}.pdf"
    
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/pdf'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

# FUNCIÓN PRINCIPAL DE PDF REPORTE MASIVO

def draw_report_logo_and_page_number(canvas, doc):
    """Callback para dibujar el encabezado y pie de página en reportes masivos."""
    canvas.saveState()
    width, height = doc.pagesize

    page_number = canvas.getPageNumber()

    ruta_imagen = HEADER_IMAGE

    if page_number == 1 and os.path.exists(ruta_imagen):
        try:
            img = ImageReader(ruta_imagen)
            img_width, img_height = img.getSize()
            scale = min(1.0, 700 / img_width)
            draw_width = img_width * scale
            draw_height = img_height * scale
            x_center = (width - draw_width) / 2
            y_top = height - draw_height - 10
            canvas.drawImage(ruta_imagen, x=x_center, y=y_top, width=draw_width, height=draw_height)
        except Exception as e:
            logger.error(f"Error ReportLab al dibujar el encabezado en PDF: {e}")
            pass

    canvas.setFont('Helvetica', 8)
    footer_text = f"Página {page_number}"

    canvas.drawString(width - 70, 30, footer_text)
    canvas.drawString(36, 30, f"Reporte generado el: {timezone.now().strftime('%d/%m/%Y %H:%M')}")

    canvas.restoreState()


def generar_pdf_reporte(queryset, filtros_aplicados):

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=36,
        rightMargin=36,
        topMargin=110, 
        bottomMargin=40
    )

    Story = []
    styles = getSampleStyleSheet()

    # Definición de estilos
    styles.add(ParagraphStyle(name='CenteredTitle', alignment=TA_CENTER, fontSize=16, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(
        name='FilterTextLeft',
        alignment=TA_LEFT,
        fontSize=9, 
        fontName='Helvetica', 
        spaceAfter=2,
        leftIndent=0,
        firstLineIndent=0,
        leading=12 
    ))
    styles.add(ParagraphStyle(name='ResumenTitleLeft', alignment=TA_LEFT, fontSize=11, fontName='Helvetica-Bold', spaceBefore=5, spaceAfter=5, firstLineIndent=0, leftIndent=0))

    total_registros = queryset.count()
    total_monto_bs = queryset.aggregate(total=Sum('total_monto_bs'))['total'] or Decimal(0)

    Story.append(Paragraph("REPORTE DE RECIBOS DE PAGO", styles['CenteredTitle']))
    Story.append(Spacer(1, 10))

    periodo_str = filtros_aplicados.get('periodo', 'Todos los períodos')
    estado_str = filtros_aplicados.get('estado', 'Todos los estados')
    categorias_str = filtros_aplicados.get('categorias', 'Todas las categorías')
    
    Story.append(Paragraph(f"<b>Período:</b> {periodo_str}", styles['FilterTextLeft']))
    Story.append(Paragraph(f"<b>Estado:</b> {estado_str}, <b>Categorías:</b> {categorias_str}", styles['FilterTextLeft']))
    Story.append(Spacer(1, 8))


    table_data = []
    table_headers = [
        'Recibo', 'Nombre', 'Cédula/RIF', 'Monto (Bs)', 'Fecha', 'Estado',
        'Transferencia', 'Concepto'
    ]
    table_data.append(table_headers)

    col_widths = [
        0.7 * inch, 1.7 * inch, 1.1 * inch, 1.0 * inch, 0.8 * inch, 0.9 * inch, 1.3 * inch, 2.5 * inch
    ]

    for recibo in queryset:
        concepto_paragrah = Paragraph(recibo.concepto.strip() if recibo.concepto else '', styles['FilterTextLeft']) 
        
        table_data.append([
            "{:04d}".format(recibo.numero_recibo) if recibo.numero_recibo else '', 
            recibo.nombre,
            recibo.rif_cedula_identidad,
            format_currency(recibo.total_monto_bs),
            recibo.fecha.strftime('%d/%m/%Y'),
            recibo.estado,
            recibo.numero_transferencia if recibo.numero_transferencia else '',
            concepto_paragrah 
        ])

    table = Table(table_data, colWidths=col_widths) 

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), CUSTOM_BLUE_DARK_TABLE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'), 
        ('ALIGN', (4, 1), (4, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, CUSTOM_GREY_VERY_LIGHT]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (7, 1), (7, -1), 'TOP'), 
        ('ALIGN', (7, 1), (7, -1), 'LEFT'),
    ]))

    Story.append(table)
    Story.append(Spacer(1, 20))


    Story.append(Paragraph("RESUMEN DEL REPORTE:", styles['ResumenTitleLeft']))
    Story.append(Paragraph(f"<b>Total de Recibos:</b> {total_registros}", styles['FilterTextLeft']))
    Story.append(Paragraph(f"<b>Monto Total Bs:</b> {format_currency(total_monto_bs)}", styles['FilterTextLeft']))
    Story.append(Spacer(1, 1))
    Story.append(Paragraph(f"<b>Período Filtrado:</b> {periodo_str}", styles['FilterTextLeft']))
    Story.append(Paragraph(f"<b>Estado Filtrado:</b> {estado_str}", styles['FilterTextLeft']))
    Story.append(Paragraph(f"<b>Categorías Filtradas:</b> {categorias_str}", styles['FilterTextLeft']))

    logo_footer_callback = lambda canvas, doc: draw_report_logo_and_page_number(
        canvas, doc
    )

    doc.build(
        Story,
        onFirstPage=logo_footer_callback,
        onLaterPages=logo_footer_callback
    )

    buffer.seek(0)

    filename = f"Reporte_Recibos_PDF_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/pdf'
    )
    response['Content-Disposition'] = f'attachment;filename="{filename}"'
    return response