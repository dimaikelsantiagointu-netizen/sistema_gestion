import pandas as pd
from django.db import transaction
from django.db.models import Max, Sum
from decimal import Decimal, InvalidOperation
from datetime import date 
import logging
import re
import io
from django.http import HttpResponse
from django.utils import timezone

from .constants import CATEGORY_CHOICES_MAP 

logger = logging.getLogger(__name__)


def to_boolean(value):
    """Convierte valores comunes de Excel (NaN, SI, X, 1, etc.) a Booleano."""
    if pd.isna(value):
        return False
    # La X es la marca principal, debe estar aquí.
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


def importar_recibos_desde_excel(archivo_excel):
    from .models import Recibo 

    RIF_COL = 'rif_cedula_identidad'

    try:
        COLUMNAS_CANONICAS = [
            'estado', 'nombre', RIF_COL, 'direccion_inmueble', 'ente_liquidado',
            'categoria1', 'categoria2', 'categoria3', 'categoria4', 'categoria5',
            'categoria6', 'categoria7', 'categoria8', 'categoria9', 'categoria10',
            'gastos_administrativos', 'tasa_dia', 'total_monto_bs', 
            'numero_transferencia', 'conciliado', 'fecha', 'concepto' 
        ]
        
        df = pd.read_excel(
            archivo_excel, 
            sheet_name='Hoja2', 
            header=3, 
            nrows=1 
        )
        
        if df.empty:
             return False, "Error: El archivo Excel está vacío o la hoja 'Hoja2' no contiene datos en el rango esperado (Fila 5).", None

        fila_datos = df.iloc[0] 
        
        if len(fila_datos) != len(COLUMNAS_CANONICAS):
            return False, f"Error: Se encontraron {len(fila_datos)} valores, pero se esperaban {len(COLUMNAS_CANONICAS)}. El Excel tiene columnas vacías.", None
            
        fila_mapeada = dict(zip(COLUMNAS_CANONICAS, fila_datos.tolist()))
        
        rif_cedula_raw = str(fila_mapeada.get(RIF_COL, '')).strip()
        
        if not rif_cedula_raw:
             return False, "El registro no tiene RIF/Cédula y no se puede procesar.", None
            
        logger.info(f"ÉXITO EN LECTURA: Se encontró el registro con RIF: {rif_cedula_raw}")
        
        data_a_insertar = {}
        
        with transaction.atomic():
            ultimo_recibo = Recibo.objects.aggregate(Max('numero_recibo'))['numero_recibo__max']
            data_a_insertar['numero_recibo'] = (ultimo_recibo or 0) + 1
            
            data_a_insertar['estado'] = str(fila_mapeada.get('estado', '')).strip().upper() 
            data_a_insertar['nombre'] = str(fila_mapeada.get('nombre', '')).strip().title()
            data_a_insertar['rif_cedula_identidad'] = str(rif_cedula_raw).strip().replace('.', '').replace('-', '').replace(' ', '').upper()
            data_a_insertar['direccion_inmueble'] = str(fila_mapeada.get('direccion_inmueble', 'DIRECCION NO ESPECIFICADA')).strip().title()
            data_a_insertar['ente_liquidado'] = str(fila_mapeada.get('ente_liquidado', 'ENTE NO ESPECIFICADO')).strip().title()
            data_a_insertar['numero_transferencia'] = str(fila_mapeada.get('numero_transferencia', '')).strip().upper()
            data_a_insertar['concepto'] = str(fila_mapeada.get('concepto', '')).strip().title()
            
            for i in range(1, 11):
                 key = f'categoria{i}'
                 data_a_insertar[key] = to_boolean(fila_mapeada.get(key))

            data_a_insertar['conciliado'] = to_boolean(fila_mapeada.get('conciliado'))

            data_a_insertar['gastos_administrativos'] = limpiar_y_convertir_decimal(fila_mapeada.get('gastos_administrativos', 0))
            data_a_insertar['tasa_dia'] = limpiar_y_convertir_decimal(fila_mapeada.get('tasa_dia', 0))
            data_a_insertar['total_monto_bs'] = limpiar_y_convertir_decimal(fila_mapeada.get('total_monto_bs', 0))
            
            fecha_excel = fila_mapeada.get('fecha')
            
            if pd.isna(fecha_excel) or str(fecha_excel).strip() == "":
                raise ValueError("El campo 'FECHA' es obligatorio y está vacío.") 
            
            if isinstance(fecha_excel, str) and fecha_excel.strip().upper() == 'FECHA':
                raise ValueError("El campo 'FECHA' contiene la palabra 'FECHA'. Por favor, ingrese una fecha válida.")

            try:
                fecha_objeto = pd.to_datetime(fecha_excel, errors='raise')

                if pd.isna(fecha_objeto):
                    raise ValueError("Formato de fecha inválido.")
                
                data_a_insertar['fecha'] = fecha_objeto.date()
                
            except Exception as e:
                logger.error(f"Error al convertir fecha '{fecha_excel}': {e}")
                raise ValueError(f"Formato de fecha no reconocido para el valor: {fecha_excel}. Use formatos estándar.")


            recibo_creado = Recibo.objects.create(**data_a_insertar)
            
            return True, f"Se generó el recibo N° {recibo_creado.numero_recibo} para {data_a_insertar['nombre']} exitosamente. Listo para PDF.", recibo_creado.pk

    except Exception as e:
        logger.error(f"FALLO DE VALIDACIÓN en el registro: {e}")
        return False, f"Fallo en la carga: Error de validación de datos (revisar consola): {str(e)}", None
    
    
#Generar reporte en excel modificaremos
def generar_reporte_excel(request_filters, queryset, filtros_aplicados): 
    """
    Genera un reporte Excel (.xlsx) con dos hojas: 'Recibos' (datos) e 
    'info_reporte' (metadatos de filtrado), sin la fila de Total General en la hoja 'Recibos'.
    
    Argumentos:
        request_filters (QueryDict): Los parámetros de filtro originales (request.GET).
        queryset (QuerySet): El QuerySet de Recibos ya filtrado.
        filtros_aplicados (dict): Diccionario que contiene el detalle de los filtros aplicados 
                                  por el usuario (para la hoja info_reporte).
    """
    # 1. Preparar la Hoja 'Recibos' (Datos Detallados)
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

    # 2. Preparar la Hoja 'info_reporte' (Metadatos)
    
    # NOTA: Mantenemos el cálculo del total aquí ya que SÍ se usa en la hoja 'info_reporte'
    total_registros = queryset.count()
    total_monto_bs = queryset.aggregate(total=Sum('total_monto_bs'))['total'] or Decimal(0)
    
    info_data = [
        ['Fecha de Generación', timezone.now().strftime('%Y-%m-%d %H:%M:%S')],
        ['Período del Reporte', filtros_aplicados.get('periodo', 'Todos los períodos')],
        ['Estado Filtrado', filtros_aplicados.get('estado', 'Todos los estados')],
        ['Categorías Filtradas', filtros_aplicados.get('categorias', 'Todas las categorías')],
        ['Total de Registros', total_registros],
        ['Monto Total (Bs)', total_monto_bs], # ¡Se mantiene en info_reporte!
    ]
    info_df = pd.DataFrame(info_data, columns=['Parámetro', 'Valor'])

    # 3. Generar el Archivo Excel con Pandas y XlsxWriter
    
    df_recibos = pd.DataFrame(data, columns=headers)
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        
        # --- Hoja 1: info_reporte ---
        info_df.to_excel(writer, index=False, sheet_name='info_reporte')
        
        # --- Hoja 2: Recibos ---
        df_recibos.to_excel(writer, index=False, sheet_name='Recibos', startrow=0, header=True)
        
        # --- Aplicar Formato a la Hoja 'Recibos' ---
        workbook = writer.book
        worksheet_recibos = writer.sheets['Recibos']
        
        money_format = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})
        bold_format = workbook.add_format({'bold': True, 'bg_color': '#EAEAEA'})
        
        # Ancho de columnas
        worksheet_recibos.set_column('A:A', 15) # 0: Número Recibo
        worksheet_recibos.set_column('B:C', 25) # 1: Nombre, 2: Cédula
        worksheet_recibos.set_column('D:D', 12) # 3: Fecha
        worksheet_recibos.set_column('E:E', 15) # 4: Estado
        worksheet_recibos.set_column('F:F', 18, money_format) # 5: Monto Total (Bs.)
        worksheet_recibos.set_column('G:G', 20) # 6: N° Transferencia
        worksheet_recibos.set_column('H:H', 40) # 7: Concepto
        worksheet_recibos.set_column('I:I', 50) # 8: Categorías
        
        # Formato para el encabezado (reiterar)
        for col_num, value in enumerate(headers):
            worksheet_recibos.write(0, col_num, value, bold_format)
            
        # ❌ Se elimina el código que escribía la fila de 'TOTAL GENERAL'
        
        # --- Aplicar Formato a la Hoja 'info_reporte' ---
        worksheet_info = writer.sheets['info_reporte']
        worksheet_info.set_column('A:A', 30) # Parámetro
        worksheet_info.set_column('B:B', 40) # Valor
        
        # Formato para el encabezado
        worksheet_info.write(0, 0, 'Parámetro', bold_format)
        worksheet_info.write(0, 1, 'Valor', bold_format)
    
    output.seek(0)
    
    # 4. Devolver la Respuesta HTTP
    filename = f"Reporte_Recibos_Masivo_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    response = HttpResponse(
        output, 
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# Generar reportes en formato pdf aun no implementado
def generar_pdf_reporte(queryset):
    """
    Genera un reporte PDF tabular de resumen a partir de un QuerySet filtrado.
    """
    raise NotImplementedError(
        "La funcionalidad de Reporte PDF tabular aún no está implementada. "
        "Debe usar una librería como ReportLab o WeasyPrint para generar tablas."
    )
    