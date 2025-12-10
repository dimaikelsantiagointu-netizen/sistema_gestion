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

# 🚨 Importaciones de Constantes y Utilerías
# Mantenemos las constantes aquí, pero el modelo Recibo lo movemos abajo.
from .constants import CATEGORY_CHOICES_MAP 

logger = logging.getLogger(__name__)

# --- FUNCIONES DE UTILIDAD ---

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

# --- FUNCIÓN PRINCIPAL DE IMPORTACIÓN ---

def importar_recibos_desde_excel(archivo_excel):
    # 🚨 Importación del Modelo SOLO dentro de la función donde se usa
    from .models import Recibo 

    RIF_COL = 'rif_cedula_identidad'

    try:
        # 1. Nombres Canónicos (21 columnas de datos)
        COLUMNAS_CANONICAS = [
            'estado', 'nombre', RIF_COL, 'direccion_inmueble', 'ente_liquidado',
            'categoria1', 'categoria2', 'categoria3', 'categoria4', 'categoria5',
            'categoria6', 'categoria7', 'categoria8', 'categoria9', 'categoria10',
            'gastos_administrativos', 'tasa_dia', 'total_monto_bs', 
            'numero_transferencia', 'conciliado', 'fecha', 'concepto' 
        ]
        
        # 2. LECTURA de Excel
        df = pd.read_excel(
            archivo_excel, 
            sheet_name='Hoja2', 
            header=3, # La fila con el índice 3 (Fila 4) es el encabezado
            nrows=1 # Lee SOLO UNA fila de datos (Fila 5)
        )
        
        # ... (Validación de df.empty, fila_datos y columnas) ...
        if df.empty:
             # 🛑 RETURN DE FALLO
             return False, "Error: El archivo Excel está vacío o la hoja 'Hoja2' no contiene datos en el rango esperado (Fila 5).", None

        fila_datos = df.iloc[0] 
        
        if len(fila_datos) != len(COLUMNAS_CANONICAS):
            # 🛑 RETURN DE FALLO
            return False, f"Error: Se encontraron {len(fila_datos)} valores, pero se esperaban {len(COLUMNAS_CANONICAS)}. El Excel tiene columnas vacías.", None
            
        fila_mapeada = dict(zip(COLUMNAS_CANONICAS, fila_datos.tolist()))
        
        # --- VALIDACIÓN DEL RIF ---
        rif_cedula_raw = str(fila_mapeada.get(RIF_COL, '')).strip()
        
        if not rif_cedula_raw:
             # 🛑 RETURN DE FALLO
             return False, "El registro no tiene RIF/Cédula y no se puede procesar.", None
            
        logger.info(f"ÉXITO EN LECTURA: Se encontró el registro con RIF: {rif_cedula_raw}")
        
        data_a_insertar = {}
        
        # --- B. TRANSACCIÓN Y MAPEO DE DATOS ---
        with transaction.atomic():
            # Obtener y asignar nuevo número de recibo
            ultimo_recibo = Recibo.objects.aggregate(Max('numero_recibo'))['numero_recibo__max']
            data_a_insertar['numero_recibo'] = (ultimo_recibo or 0) + 1
            
            # ... (Mapeo y normalización de todos los campos) ...
            data_a_insertar['estado'] = str(fila_mapeada.get('estado', '')).strip().upper() 
            data_a_insertar['nombre'] = str(fila_mapeada.get('nombre', '')).strip().title()
            data_a_insertar['rif_cedula_identidad'] = str(rif_cedula_raw).strip().replace('.', '').replace('-', '').replace(' ', '').upper()
            data_a_insertar['direccion_inmueble'] = str(fila_mapeada.get('direccion_inmueble', 'DIRECCION NO ESPECIFICADA')).strip().title()
            data_a_insertar['ente_liquidado'] = str(fila_mapeada.get('ente_liquidado', 'ENTE NO ESPECIFICADO')).strip().title()
            data_a_insertar['numero_transferencia'] = str(fila_mapeada.get('numero_transferencia', '')).strip().upper()
            data_a_insertar['concepto'] = str(fila_mapeada.get('concepto', '')).strip().title()
            
            # Categorías
            for i in range(1, 11):
                 key = f'categoria{i}'
                 data_a_insertar[key] = to_boolean(fila_mapeada.get(key))

            data_a_insertar['conciliado'] = to_boolean(fila_mapeada.get('conciliado'))

            # Decimales
            data_a_insertar['gastos_administrativos'] = limpiar_y_convertir_decimal(fila_mapeada.get('gastos_administrativos', 0))
            data_a_insertar['tasa_dia'] = limpiar_y_convertir_decimal(fila_mapeada.get('tasa_dia', 0))
            data_a_insertar['total_monto_bs'] = limpiar_y_convertir_decimal(fila_mapeada.get('total_monto_bs', 0))
            
            # Validación y Conversión de Fecha
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
                # Lanzamos la excepción para que el bloque 'try...except' principal la capture
                raise ValueError(f"Formato de fecha no reconocido para el valor: {fecha_excel}. Use formatos estándar.")


            # Creación del Recibo
            recibo_creado = Recibo.objects.create(**data_a_insertar)
            
            # 🛑 RETURN DE ÉXITO (Ahora devolvemos el PK)
            return True, f"Se generó el recibo N° {recibo_creado.numero_recibo} para {data_a_insertar['nombre']} exitosamente. Listo para PDF.", recibo_creado.pk

    except Exception as e:
        logger.error(f"FALLO DE VALIDACIÓN en el registro: {e}")
        # 🛑 RETURN DE FALLO (Ahora devolvemos None)
        return False, f"Fallo en la carga: Error de validación de datos (revisar consola): {str(e)}", None
    
    
# --- FUNCIÓN PRINCIPAL DE REPORTE EXCEL ---

def generar_excel_recibos(queryset): # <-- CORREGIDO: Sin indentación
    """
    Genera un reporte Excel (.xlsx) a partir de un QuerySet filtrado de Recibo.
    """
    # 🚨 OPTIMIZACIÓN: Ya no necesitamos importar CATEGORY_CHOICES_MAP aquí,
    # porque ya está importada al inicio del archivo desde .constants.

    # 1. Preparar la Lista de Datos
    data = []
    
    # Nombres de las categorías que usaremos en las columnas
    category_names = list(CATEGORY_CHOICES_MAP.values()) 
    
    # Definir el encabezado del reporte (Columnas)
    headers = [
        'N° Recibo', 
        'Fecha', 
        'Estado', 
        'Nombre Cliente', 
        'RIF/Cédula', 
        'Dirección', 
        'Ente Liquidado', 
        'Gastos Adm.',
        'Tasa Día',
        'Monto Total (Bs)',
        'N° Transferencia',
        'Conciliado',
        'Concepto',
    ] + category_names # Añadir las 10 columnas de categoría
    
    # 2. Iterar sobre el QuerySet
    for recibo in queryset:
        row = [
            recibo.numero_recibo,
            recibo.fecha.strftime('%Y-%m-%d'),
            recibo.estado,
            recibo.nombre,
            recibo.rif_cedula_identidad,
            recibo.direccion_inmueble,
            recibo.ente_liquidado,
            recibo.gastos_administrativos,
            recibo.tasa_dia,
            recibo.total_monto_bs,
            recibo.numero_transferencia,
            'Sí' if recibo.conciliado else 'No',
            recibo.concepto,
        ]
        
        # 3. Mapear los campos booleanos a 'Sí' o 'No' para el reporte
        category_status = []
        for i in range(1, 11):
            field_name = f'categoria{i}'
            # Usamos getattr() para acceder dinámicamente al valor booleano (True/False)
            is_active = getattr(recibo, field_name) 
            category_status.append('Sí' if is_active else 'No')
            
        data.append(row + category_status)

    # 4. Cálculo de Totales 
    total_sum_bs = queryset.aggregate(total=Sum('total_monto_bs'))['total'] or Decimal(0)
    
    # 5. Crear el DataFrame y el Archivo Excel
    df = pd.DataFrame(data, columns=headers)
    
    # Añadir una fila de totales (Ajustada para que el Total caiga en la columna correcta)
    total_row = [''] * (len(headers) - 1) + [total_sum_bs] 
    df.loc['Total'] = total_row
    
    output = io.BytesIO()
    
    # Asegúrate de tener 'xlsxwriter' instalado en tu venv: pip install xlsxwriter
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte Recibos')
        
        # 🚨 Detalle: Formatear la fila de totales
        workbook = writer.book
        worksheet = writer.sheets['Reporte Recibos']
        
        # Formato negrita para el texto del total
        bold_format = workbook.add_format({'bold': True})
        
        # Índice de la última fila y de la columna 'Monto Total (Bs)'
        last_row = len(df) # Fila 'Total'
        total_col_index = headers.index('Monto Total (Bs)') 
        
        # Escribir el texto 'TOTAL GENERAL:' en negrita
        worksheet.write(last_row, total_col_index - 1, 'TOTAL GENERAL:', bold_format)
        
    output.seek(0)
    
    # 6. Crear la Respuesta HTTP
    filename = f"Reporte_Recibos_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    response = HttpResponse(
        output, 
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
    
# --- FUNCIÓN PRINCIPAL DE REPORTE PDF ---

def generar_pdf_reporte(queryset): # <-- CORREGIDO: Sin indentación
    """
    Genera un reporte PDF tabular de resumen a partir de un QuerySet filtrado.
    """
    raise NotImplementedError(
        "La funcionalidad de Reporte PDF tabular aún no está implementada. "
        "Debe usar una librería como ReportLab o WeasyPrint para generar tablas."
    )