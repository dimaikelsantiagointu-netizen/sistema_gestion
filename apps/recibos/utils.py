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
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.units import inch
from django.conf import settings
from unidecode import unidecode
from .constants import CATEGORY_CHOICES_MAP
from .models import Recibo

logger = logging.getLogger(__name__)


def to_boolean(value):
    """Convierte valores comunes de Excel (NaN, SI, X, 1, etc.) a Booleano."""
    if pd.isna(value):
        return False
    return str(value).strip().lower() in ['sí', 'si', 'true', '1', 'x', 'y']


def limpiar_y_convertir_decimal(value):
    """Limpia cualquier carácter no numérico y convierte a Decimal."""
    if pd.isna(value) or value is None:
        return Decimal(0)

    s = str(value).strip()
    if not s or s in ['-', 'n/a', 'no aplica']:
        return Decimal(0)

    s_limpio = re.sub(r'[^\d,\.]', '', s)
    s_final = s_limpio.replace(',', '.')

    if s_final.count('.') > 1:
        partes = s_final.rsplit('.', 1)
        s_final = partes[0].replace('.', '') + '.' + partes[1]

    try:
        if not s_final:
            return Decimal(0)

        return Decimal(s_final)
    except InvalidOperation:
        logger.error(f"Error fatal de conversión de Decimal: '{s_final}' (original: '{value}')")
        return Decimal(0)


def format_currency(amount):
    """Formatea el monto como moneda (ej: 1.234,56)."""
    try:
        amount_decimal = Decimal(amount)
        # Usa el formato español para miles y decimales
        formatted = "{:,.2f}".format(amount_decimal).replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted
    except Exception:
        return "0,00"


def importar_recibos_desde_excel(archivo_excel):
    """
    Lee todas las filas del archivo Excel (a partir de la fila 4) y genera
    un recibo por cada fila de datos válida, asignando números de recibo consecutivos.
    """
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
        try:
            df = pd.read_excel(
                archivo_excel,
                sheet_name='Hoja2',
                header=3,
                dtype={'fecha': str}
            )
        except ValueError:
            logger.error("Error: La hoja 'Hoja2' no existe o la estructura del Excel es incorrecta.")
            return False, "Error de archivo: Asegúrate de que existe la hoja 'Hoja2' y el formato es válido.", None

        df.dropna(how='all', inplace=True)

        if df.empty:
            return False, "El archivo Excel está vacío o la hoja 'Hoja2' no contiene datos válidos (Fila 5 en adelante).", None

        if df.shape[1] < len(COLUMNAS_CANONICAS):
            return False, f"Error: Se encontraron {df.shape[1]} columnas de datos, pero se esperaban {len(COLUMNAS_CANONICAS)}. Revise que el encabezado comience correctamente en la Fila 4.", None

        df = df.iloc[:, :len(COLUMNAS_CANONICAS)]
        df.columns = COLUMNAS_CANONICAS


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
                    raise ValueError(f"Fila {fila_numero}: El campo RIF/Cédula es obligatorio y está vacío para un registro con Nombre: {nombre_raw}.")

                data_a_insertar = {}
                data_a_insertar['numero_recibo'] = consecutivo_actual

                estado_raw = str(fila_datos.get('estado', '')).strip()
                if estado_raw:
                    data_a_insertar['estado'] = unidecode(estado_raw).upper()
                else:
                    data_a_insertar['estado'] = ''

                data_a_insertar['nombre'] = str(nombre_raw).title()
                data_a_insertar['rif_cedula_identidad'] = str(rif_cedula_raw).strip().replace('.', '').replace('-', '').replace(' ', '').upper()
                data_a_insertar['direccion_inmueble'] = str(fila_datos.get('direccion_inmueble', 'DIRECCION NO ESPECIFICADA')).strip().title()
                data_a_insertar['ente_liquidado'] = str(fila_datos.get('ente_liquidado', 'ENTE NO ESPECIFICADO')).strip().title()
                data_a_insertar['numero_transferencia'] = str(fila_datos.get('numero_transferencia', '')).strip().upper()
                data_a_insertar['concepto'] = str(fila_datos.get('concepto', '')).strip().title()

                for i in range(1, 11):
                    key = f'categoria{i}'
                    data_a_insertar[key] = to_boolean(fila_datos.get(key))

                data_a_insertar['conciliado'] = to_boolean(fila_datos.get('conciliado'))

                data_a_insertar['gastos_administrativos'] = limpiar_y_convertir_decimal(fila_datos.get('gastos_administrativos', 0))
                data_a_insertar['tasa_dia'] = limpiar_y_convertir_decimal(fila_datos.get('tasa_dia', 0))
                data_a_insertar['total_monto_bs'] = limpiar_y_convertir_decimal(fila_datos.get('total_monto_bs', 0))

                fecha_excel = fila_datos.get('fecha')

                fecha_str = str(fecha_excel).strip()
                if not fecha_str or fecha_str.lower() in ['nan', 'nat', 'none']:
                    raise ValueError(f"Fila {fila_numero}: El campo 'FECHA' es obligatorio y es leído como VACÍO/NULO.")

                try:
                    fecha_objeto = pd.to_datetime(fecha_str, errors='coerce', dayfirst=True)

                    if pd.isna(fecha_objeto):
                        raise ValueError(f"Formato de fecha inválido o irrecuperable (Valor: {fecha_str}).")

                    data_a_insertar['fecha'] = fecha_objeto.date()

                except Exception as e:
                    logger.error(f"Fila {fila_numero}: Error al convertir fecha '{fecha_str}': {e}")
                    raise ValueError(f"Fila {fila_numero}: Error de formato de fecha: {fecha_str}.")


                recibo_creado = Recibo.objects.create(**data_a_insertar)
                recibos_creados_pks.append(recibo_creado.pk)
                consecutivo_actual += 1
                logger.info(f"ÉXITO: Recibo N°{recibo_creado.numero_recibo} generado para {data_a_insertar['nombre']} (Fila {fila_numero}).")


            if recibos_creados_pks:
                total_creados = len(recibos_creados_pks)
                # ✅ CORRECCIÓN: Usar el número de inicio y fin correctamente formateado con zfill
                primer_num = str(consecutivo_actual - total_creados).zfill(4)
                ultimo_num = str(consecutivo_actual - 1).zfill(4)

                mensaje = f"Importación masiva exitosa. Se generaron {total_creados} recibos, desde N°{primer_num} hasta N°{ultimo_num}."

                logger.info("Retornando éxito de la función importar_recibos_desde_excel.")
                return True, mensaje, recibos_creados_pks
            else:
                mensaje = "Importación terminada. No se encontraron registros válidos para crear recibos (todas las filas vacías o sin RIF)."
                logger.warning("Retornando éxito sin recibos creados.")
                return True, mensaje, []

    except Exception as e:
        error_message = f"FALLO FATAL DE CARGA: {e}"
        logger.error(error_message, exc_info=True)
        return False, f"Fallo en la carga de Excel: {str(e)}", None


def generar_reporte_excel(request_filters, queryset, filtros_aplicados):
    """
    Genera un reporte Excel (.xlsx) con dos hojas: 'Recibos' (datos detallados, sin totales) y
    'info_reporte' (metadatos de filtrado y totales).
    """
    data = []

    headers = [
        'Número Recibo',
        'Nombre',
        'Cédula/RIF',
        'Fecha',
        'Estado',
        'Monto Total (Bs.)',
        'N° Transferencia',
        'Concepto',
        'Categorías'
    ]

    for recibo in queryset:

        categoria_detalle_nombres = []
        for i in range(1, 11):
            field_name = f'categoria{i}'

            if getattr(recibo, field_name):
                nombre_categoria = CATEGORY_CHOICES_MAP.get(field_name, f'Categoría {i} (Desconocida)')
                categoria_detalle_nombres.append(nombre_categoria)

        categorias_concatenadas = ','.join(categoria_detalle_nombres)

        row = [
            "{:04d}".format(recibo.numero_recibo), 
            recibo.nombre,
            recibo.rif_cedula_identidad,
            recibo.fecha.strftime('%Y-%m-%d'),
            recibo.estado,
            recibo.total_monto_bs,
            recibo.numero_transferencia,
            recibo.concepto.strip(),
            categorias_concatenadas
        ]
        data.append(row)


    total_registros = queryset.count()
    total_monto_bs = queryset.aggregate(total=Sum('total_monto_bs'))['total'] or Decimal(0)

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

        money_format = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})
        bold_format = workbook.add_format({'bold': True, 'bg_color': '#EAEAEA'})

        worksheet_recibos.set_column('A:A', 15)
        worksheet_recibos.set_column('B:C', 25)
        worksheet_recibos.set_column('D:D', 12)
        worksheet_recibos.set_column('E:E', 15)
        worksheet_recibos.set_column('F:F', 18, money_format)
        worksheet_recibos.set_column('G:G', 20)
        worksheet_recibos.set_column('H:H', 40)
        worksheet_recibos.set_column('I:I', 50)

        for col_num, value in enumerate(headers):
            worksheet_recibos.write(0, col_num, value, bold_format)

        worksheet_info = writer.sheets['info_reporte']
        worksheet_info.set_column('A:A', 30)
        worksheet_info.set_column('B:B', 40)

        worksheet_info.write(0, 0, 'Parámetro', bold_format)
        worksheet_info.write(0, 1, 'Valor', bold_format)

    output.seek(0)

    filename = f"Reporte_Recibos_Masivo_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment;filename="{filename}"'
    return response


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

# --- FUNCIONES AUXILIARES PARA EL PDF UNITARIO (COPIADAS Y ADAPTADAS DE VIEWS.PY) ---

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

# ---------------------------------------------------------------------------------


# ---------------------------------------------------------------------------------
# 🚀 FUNCIÓN CLAVE AÑADIDA: DESCARGA DIRECTA DE RECIBO UNITARIO
# ---------------------------------------------------------------------------------
def generar_pdf_recibo_unitario(recibo_obj):
    """
    Genera el contenido del PDF individual para un recibo (similar a generate_receipt_pdf)
    y retorna directamente el HttpResponse para forzar la descarga.
    """
    nombre = recibo_obj.nombre
    cedula = recibo_obj.rif_cedula_identidad
    direccion = recibo_obj.direccion_inmueble
    monto = recibo_obj.total_monto_bs
    num_transf = recibo_obj.numero_transferencia if recibo_obj.numero_transferencia else ''
    fecha = recibo_obj.fecha.strftime("%d/%m/%Y")
    concepto = recibo_obj.concepto
    estado = recibo_obj.estado

    if recibo_obj.numero_recibo:
        num_recibo = str(recibo_obj.numero_recibo).zfill(4)
    else:
        num_recibo = 'N/A'

    categorias = {
        f'categoria{i}': getattr(recibo_obj, f'categoria{i}') for i in range(1, 11)
    }

    monto_formateado = format_currency(monto)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    current_y = height - 50
    y_top = height - 50

    # DIBUJAR ENCABEZADO
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

    # Coordenadas
    X1_TITLE = 60
    X1_DATA = 160
    X2_TITLE = 310
    X2_DATA = 470

    y_line = current_y

    # FILA 1
    y_line = draw_text_line_unit(c, "Estado:", X1_TITLE, y_line, is_bold=True)
    draw_text_line_unit(c, estado, X1_DATA, y_line + 15, is_bold=False)
    draw_text_line_unit(c, "Nº Recibo:", X2_TITLE, y_line, is_bold=True)
    draw_text_line_unit(c, num_recibo, X2_DATA, y_line + 15, is_bold=False)
    y_line -= 5

    # FILA 2
    y_line = draw_text_line_unit(c, "Recibí de:", X1_TITLE, y_line, is_bold=True)
    draw_text_line_unit(c, nombre, X1_DATA, y_line + 15, is_bold=False)
    draw_text_line_unit(c, "Monto Recibido (Bs.):", X2_TITLE, y_line, is_bold=True)
    draw_text_line_unit(c, monto_formateado, X2_DATA, y_line + 15, is_bold=False)
    y_line -= 5

    # FILA 3
    y_line = draw_text_line_unit(c, "Rif/C.I:", X1_TITLE, y_line, is_bold=True)
    draw_text_line_unit(c, cedula, X1_DATA, y_line + 15, is_bold=False)
    draw_text_line_unit(c, "Nº Transferencia:", X2_TITLE, y_line, is_bold=True)
    draw_text_line_unit(c, num_transf, X2_DATA, y_line + 15, is_bold=False)
    y_line -= 5

    # FILA 4
    y_line = draw_text_line_unit(c, "Dirección:", X1_TITLE, y_line, is_bold=True)
    draw_text_line_unit(c, direccion, X1_DATA, y_line + 15, is_bold=False)
    draw_text_line_unit(c, "Fecha:", X2_TITLE, y_line, is_bold=True)
    draw_text_line_unit(c, fecha, X2_DATA, y_line + 15, is_bold=False)
    y_line -= 5

    # FILA 5
    y_line = draw_text_line_unit(c, "Concepto:", X1_TITLE, y_line, is_bold=True)
    draw_text_line_unit(c, concepto, X1_DATA, y_line + 15, is_bold=False)
    current_y = y_line - 25

    # Sección de Categorías
    hay_categorias = any(categorias.values())

    if hay_categorias:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(X1_TITLE, current_y, "FORMA DE PAGO Y DESCRIPCION DE LA REGULARIZACION")
        current_y -= 25

        # (Manteniendo la estructura original para las 10 categorías)
        
        if categorias.get('categoria1', False):
            current_y = draw_text_line_unit(c, "TITULO DE TIERRA URBANA - TITULO DE ADJUDICACION EN PROPIEDAD", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line_unit(c, "Una milésima de Bolívar, Art. 58 de la Ley Especial de Regularización", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5

        if categorias.get('categoria2', False):
            current_y = draw_text_line_unit(c, "TITULO DE TIERRA URBANA - TITULO DE ADJUDICACION MAS VIVIENDA", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line_unit(c, "Una milésima de Bolívar, más gastos administrativos (140 unidades ancladas a la moneda de mayor valor estipulada por el BCV)", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5

        if categorias.get('categoria3', False):
            current_y = draw_text_line_unit(c, "VIVIENDA UNIFAMILIAR Y MULTIFAMILIAR (EDIFICIOS) TIERRA:", X1_TITLE, current_y, font_size=9, is_bold=True)
            current_y = draw_text_line_unit(c, "Municipal", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line_unit(c, "Precio: Gastos Administrativos (140 unidades ancladas a la moneda de mayor valor estipulada por el BCV)", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5

        if categorias.get('categoria4', False):
            current_y = draw_text_line_unit(c, "VIVIENDA UNIFAMILIAR Y MULTIFAMILIAR (EDIFICIOS) TIERRA:", X1_TITLE, current_y, font_size=9, is_bold=True)
            current_y = draw_text_line_unit(c, "Tierra Privada", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line_unit(c, "Precio: Gastos Administrativos (140 unidades ancladas a la moneda de mayor valor estipulada por el BCV)", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5

        if categorias.get('categoria5', False):
            current_y = draw_text_line_unit(c, "VIVIENDA UNIFAMILIAR Y MULTIFAMILIAR (EDIFICIOS) TIERRA:", X1_TITLE, current_y, font_size=9, is_bold=True)
            current_y = draw_text_line_unit(c, "Tierra INAVI o de cualquier Ente transferido al INTU", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line_unit(c, "Precio: Gastos Administrativos (140 unidades ancladas a la moneda de mayor valor estipulada por el BCV)", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5

        if categorias.get('categoria6', False):
            current_y = draw_text_line_unit(c, "EXCEDENTES:", X1_TITLE, current_y, font_size=9, is_bold=True)
            current_y = draw_text_line_unit(c, "Con título de Tierra Urbana, hasta 400 mt2 una milésima por mt2", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line_unit(c, "Según el Art 33 de la Ley Especial de Regularización", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5

        if categorias.get('categoria7', False):
            current_y = draw_text_line_unit(c, "Con Título INAVI (Gastos Administrativos):", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line_unit(c, "140 unidades ancladas a la moneda de mayor valor estipulada por el BCV)", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5

        if categorias.get('categoria8', False):
            current_y = draw_text_line_unit(c, "ESTUDIOS TÉCNICOS:", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line_unit(c, "Medición detallada de la parcela para obtener representación gráfica (plano)", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5

        if categorias.get('categoria9', False):
            current_y = draw_text_line_unit(c, "ARRENDAMIENTOS DE LOCALES COMERCIALES:", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line_unit(c, "Número de unidades establecidas en el contrato, ancladas a la moneda de mayor valor estipulada por el BCV", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5

        if categorias.get('categoria10', False):
            current_y = draw_text_line_unit(c, "ARRENDAMIENTOS DE TERRENOS", X1_TITLE, current_y, font_size=9, is_bold=True)
            c.drawString(520, current_y + 15, "X")
            current_y = draw_text_line_unit(c, "Número de unidades establecidas en el contrato, ancladas a la moneda de mayor valor estipulada por el BCV", X1_TITLE, current_y, font_size=8, is_bold=False)
            current_y -= 5

        current_y -= 70

    # Si hay desborde, crear una nueva página (aunque es poco probable para un recibo)
    if current_y < 150:
        c.showPage()
        current_y = height - 100

    # SECCIÓN DE FIRMAS
    line_width = 200
    left_line_x = (width / 2 - line_width - 20)
    right_line_x = (width / 2 + 20)

    # LÍNEAS
    c.line(left_line_x, current_y, left_line_x + line_width, current_y)
    c.line(right_line_x, current_y, right_line_x + line_width, current_y)

    # FIRMA CLIENTE
    y_sig = current_y - 15
    draw_centered_text_right_unit(c, y_sig, "Firma", left_line_x, line_width)
    y_sig -= 13
    draw_centered_text_right_unit(c, y_sig, nombre, left_line_x, line_width, is_bold=True)
    y_sig -= 12
    draw_centered_text_right_unit(c, y_sig, f"C.I./RIF: {cedula}", left_line_x, line_width, font_size=9)

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

    c.showPage()
    c.save()
    buffer.seek(0)
    
    # 🛑 RETORNA EL HTTPRESPONSE PARA DESCARGA DIRECTA 🛑
    filename = f"Recibo_N_{num_recibo}_{cedula}.pdf"
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/pdf'
    )
    # EL Content-Disposition: attachment FUERZA LA DESCARGA
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

# ---------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------


def draw_report_logo_and_page_number(canvas, doc):
    # ... (Esta función se mantiene igual)

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
        topMargin=100,
        bottomMargin=40
    )

    Story = []
    styles = getSampleStyleSheet()

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
    
    Story.append(Paragraph(
        f"<b>Período:</b> {periodo_str}",
        styles['FilterTextLeft']
    ))
    
    filtros_html = f"""
    <b>Estado:</b> {estado_str}, 
    <b>Categorías:</b> {categorias_str}
    """
    Story.append(Paragraph(filtros_html, styles['FilterTextLeft']))

    Story.append(Spacer(1, 8))


    table_data = []
    table_headers = [
        'Recibo', 'Nombre', 'Cédula/RIF', 'Monto (Bs)', 'Fecha', 'Estado',
        'Transferencia', 'Concepto'
    ]
    table_data.append(table_headers)

    col_widths = [
        0.7 * inch, # Recibo 
        1.7 * inch, # Nombre 
        1.1 * inch, # Cédula/RIF 
        1.0 * inch, # Monto (Bs) 
        0.8 * inch, # Fecha 
        0.9 * inch, # Estado 
        1.3 * inch, # Transferencia 
        2.5 * inch  # Concepto 
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
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('BACKGROUND', (0, 2), (-1, -1), CUSTOM_GREY_VERY_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (7, 1), (7, -1), 'MIDDLE'),
        ('ALIGN', (7, 1), (7, -1), 'LEFT'),
    ]))

    Story.append(table)
    Story.append(Spacer(1, 20))


    Story.append(Paragraph("RESUMEN DEL REPORTE:", styles['ResumenTitleLeft']))


    Story.append(Paragraph(
        f"<b>Total de Recibos:</b> {total_registros}",
        styles['FilterTextLeft']
    ))

    Story.append(Paragraph(
        f"<b>Monto Total Bs:</b> {format_currency(total_monto_bs)}",
        styles['FilterTextLeft']
    ))

    Story.append(Spacer(1, 1))

    Story.append(Paragraph(
        f"<b>Período Filtrado:</b> {periodo_str}",
        styles['FilterTextLeft']
    ))

    Story.append(Paragraph(
        f"<b>Estado Filtrado:</b> {estado_str}",
        styles['FilterTextLeft']
    ))

    Story.append(Paragraph(
        f"<b>Categorías Filtradas:</b> {categorias_str}",
        styles['FilterTextLeft']
    ))

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