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
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT # <- TA_RIGHT añadido
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
        return "{:,.2f}".format(amount_decimal).replace(",", "X").replace(".", ",").replace("X", ".")
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
                primer_num = consecutivo_actual - total_creados
                ultimo_num = consecutivo_actual - 1

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

        categorias_concatenadas = ', '.join(categoria_detalle_nombres)

        row = [
            recibo.numero_recibo,
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

        # Ajuste de ancho de columnas
        worksheet_recibos.set_column('A:A', 15)
        worksheet_recibos.set_column('B:C', 25)
        worksheet_recibos.set_column('D:D', 12)
        worksheet_recibos.set_column('E:E', 15)
        worksheet_recibos.set_column('F:F', 18, money_format)
        worksheet_recibos.set_column('G:G', 20)
        worksheet_recibos.set_column('H:H', 40)
        worksheet_recibos.set_column('I:I', 50)

        # Formato de encabezados
        for col_num, value in enumerate(headers):
            worksheet_recibos.write(0, col_num, value, bold_format)
        
        # Formato de info_reporte
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


# 🛑 CORRECCIÓN 1: Eliminados los argumentos innecesarios (total_registros, total_monto_bs)
def draw_report_logo_and_page_number(canvas, doc):
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

    styles.add(ParagraphStyle(name='FilterText', alignment=TA_LEFT, fontSize=9, fontName='Helvetica', spaceAfter=2))

    styles.add(ParagraphStyle(name='ResumenTitleLeft', alignment=TA_LEFT, fontSize=11, fontName='Helvetica-Bold', spaceBefore=5, spaceAfter=5, firstLineIndent=0, leftIndent=0))

    styles.add(ParagraphStyle(
        name='FilterTextLeft',
        alignment=TA_LEFT,
        fontSize=9,
        fontName='Helvetica',
        spaceAfter=2,
        leftIndent=0,
        firstLineIndent=0
    ))

    styles.add(ParagraphStyle(name='FooterText', alignment=TA_LEFT, fontSize=8, fontName='Helvetica', spaceBefore=10))

    total_registros = queryset.count()
    total_monto_bs = queryset.aggregate(total=Sum('total_monto_bs'))['total'] or Decimal(0)

    Story.append(Paragraph("REPORTE DE RECIBOS DE PAGO", styles['CenteredTitle']))
    Story.append(Spacer(1, 10))


    periodo_str = filtros_aplicados.get('periodo', 'Todos los períodos')
    estado_str = filtros_aplicados.get('estado', 'Todos los estados')
    categorias_str = filtros_aplicados.get('categorias', 'Todas las categorías')

    periodo_html = f"""
    <font size=9>
    <b>Período:</b> {periodo_str}
    </font>
    """
    Story.append(Paragraph(periodo_html, styles['FilterText']))

    filtros_html = f"""
    <font size=9>
    <b>Filtros aplicados - Estado:</b> {estado_str},
    <b>Categorías:</b> {categorias_str}
    </font>
    """
    Story.append(Paragraph(filtros_html, styles['FilterText']))

    Story.append(Spacer(1, 8))


    table_data = []
    table_headers = [
        'Recibo', 'Nombre', 'Cédula/RIF', 'Monto (Bs)', 'Fecha', 'Estado',
        'Transferencia', 'Concepto'
    ]
    table_data.append(table_headers)

    col_widths = [60, 130, 90, 80, 70, 70, 100, 120]

    for recibo in queryset:
        table_data.append([
            recibo.numero_recibo,
            recibo.nombre,
            recibo.rif_cedula_identidad,
            format_currency(recibo.total_monto_bs),
            recibo.fecha.strftime('%d/%m/%Y'),
            recibo.estado,
            recibo.numero_transferencia if recibo.numero_transferencia else '',
            recibo.concepto.strip()
        ])

    table = Table(table_data, colWidths=col_widths)

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), CUSTOM_BLUE_DARK_TABLE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'), # <- CORRECCIÓN 3: Monto alineado a la derecha
        ('ALIGN', (4, 1), (4, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('BACKGROUND', (0, 2), (-1, -1), CUSTOM_GREY_VERY_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BOX', (0, 0), (-1, -1), 0, colors.white),
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
        f"<b>Período:</b> {periodo_str}",
        styles['FilterTextLeft']
    ))

    Story.append(Paragraph(
        f"<b>Estado:</b> {estado_str}",
        styles['FilterTextLeft']
    ))

    Story.append(Paragraph(
        f"<b>Categorías:</b> {categorias_str}",
        styles['FilterTextLeft']
    ))

    Story.append(Spacer(1, 1))

    # 🛑 CORRECCIÓN 2: Se llama la función lambda sin pasar los argumentos que ya no existen
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