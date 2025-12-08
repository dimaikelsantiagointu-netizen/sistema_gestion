import pandas as pd
from django.db import transaction
from django.db.models import Max
from decimal import Decimal
from datetime import date # Necesario para la conversión de fecha
from .models import Recibo 

def to_boolean(value):
    """Convierte valores de Excel (NaN, SI, X, 1, etc.) a Booleano."""
    if pd.isna(value):
        return False
    return str(value).strip().lower() in ['sí', 'si', 'true', '1', 'x', 'x', 'y']

def importar_recibos_desde_excel(archivo_excel):
    # Variables de estado
    registros_a_crear = []
    total_errores = 0
    
    try:
        # 1. Leer el archivo Excel (header=3 ya corregido)
        df = pd.read_excel(archivo_excel, header=3)
        
        # Iniciar transacción para asegurar la integridad
        with transaction.atomic():
            
            # Obtener el último numero_recibo para continuar la secuencia
            ultimo_recibo = Recibo.objects.aggregate(Max('numero_recibo'))['numero_recibo__max']
            next_numero_recibo = (ultimo_recibo or 0) + 1
            
            # 2. Iterar sobre las filas del DataFrame (Excel)
            for index, fila in df.iterrows():
                
                # Bucle de manejo de errores por fila (para evitar el fallo "0 recibos")
                try:
                    
                    # ----------------------------------------------------
                    # A. PRE-VALIDACIÓN (Descarta Filas Completamente Vacías)
                    # ----------------------------------------------------
                    # Asume que el RIF/Cédula es un campo esencial
                    rif_cedula_raw = fila.get('RIF O CÉDULA DE IDENTIDAD')
                    if pd.isna(rif_cedula_raw) or str(rif_cedula_raw).strip() == "":
                        # Si no hay identificador, saltamos la fila (puede ser una fila de metadatos o vacía)
                        continue 
                    
                    data_a_insertar = {}
                    data_a_insertar['numero_recibo'] = next_numero_recibo
                    
                    # ----------------------------------------------------
                    # B. NORMALIZACIÓN Y CONVERSIÓN DE TIPOS
                    # ----------------------------------------------------
                    
                    # Normalización de Texto (Trujillo vs trujillo)
                    data_a_insertar['estado'] = str(fila.get('ESTADO', '')).strip().upper() # TODO A MAYÚSCULAS
                    data_a_insertar['nombre'] = str(fila.get('NOMBRE', '')).strip().title() # CAPITALIZACIÓN (Nombres Propios)
                    data_a_insertar['ente_liquidado'] = str(fila.get('ENTE LIQUIDADO', '')).strip().title()
                    
                    # Limpieza de RIF/Cédula
                    data_a_insertar['rif_cedula_identidad'] = str(rif_cedula_raw).strip().replace('.', '').replace('-', '').replace(' ', '')
                    
                    data_a_insertar['direccion_inmueble'] = str(fila.get('DIRECCION DEL INMUEBLE', '')).strip()
                    data_a_insertar['numero_transferencia'] = str(fila.get('NUMERO DE TRANSFERENCIA', '')).strip()
                    data_a_insertar['concepto'] = str(fila.get('CONCEPTO', '')).strip()
                    
                    # Categorías (Usa la función to_boolean)
                    data_a_insertar['categoria1'] = to_boolean(fila.get('1.- TITULO DE TIERRA URBANA- TITULO DE ADJUDICACION EN PROPIEDAD'))
                    data_a_insertar['categoria2'] = to_boolean(fila.get('2.- TITULO DE TIERRA URBANA-TITULO DE ADJUDICACION MAS VIVIENDA'))
                    data_a_insertar['categoria3'] = to_boolean(fila.get('Municipal'))
                    data_a_insertar['categoria4'] = to_boolean(fila.get('Tierra Privada'))
                    data_a_insertar['categoria5'] = to_boolean(fila.get('Tierra INAVI o de cualquier Ente transferido al INTU'))
                    data_a_insertar['categoria6'] = to_boolean(fila.get('4.1- Con título de Tierra Urbana, hasta 400 mt2 una milésima por mt2'))
                    data_a_insertar['categoria7'] = to_boolean(fila.get('4.2-Con Título INAVI(Gastos Administrativos):'))
                    data_a_insertar['categoria8'] = to_boolean(fila.get('5.- ESTUDIOS TECNICOS:'))
                    data_a_insertar['categoria9'] = to_boolean(fila.get('6.-ARRENDAMIENTOS DE LOCALES COMERCIALES:'))
                    data_a_insertar['categoria10'] = to_boolean(fila.get('7.- ARRENDAMIENTOS DE TERRENOS'))
                    data_a_insertar['conciliado'] = to_boolean(fila.get('CONCILIADO'))

                    # Conversión a Decimal (CRÍTICO para evitar errores de tipo)
                    # El uso de .replace(',', '.') asegura que acepte el formato español
                    data_a_insertar['gastos_administrativos'] = Decimal(str(fila.get('GASTOS ADMINISTRATIVOS (UNIDADES ANCLADAS A LA MONEDA DE MAYOR VALOR DEL BCV)', 0)).replace(',', '.').strip() or 0)
                    data_a_insertar['tasa_dia'] = Decimal(str(fila.get('TASA DEL DIA', 0)).replace(',', '.').strip() or 0)
                    data_a_insertar['total_monto_bs'] = Decimal(str(fila.get('TOTAL MONTO EN BS', 0)).replace(',', '.').strip() or 0)

                    # Conversión a Fecha (CRÍTICO)
                    fecha_excel = fila.get('FECHA')
                    if pd.isna(fecha_excel):
                        # Levanta un error si la fecha es obligatoria y está vacía
                        raise ValueError("El campo 'FECHA' es obligatorio.") 
                    
                    # Convierte el objeto de fecha de Pandas a objeto date de Python
                    data_a_insertar['fecha'] = pd.to_datetime(fecha_excel).date()

                    # Campos automáticos que necesitan ser seteados si no son auto_now_add
                    # data_a_insertar['anulado'] = False 
                    
                    # Crear el objeto Recibo (en memoria)
                    registros_a_crear.append(Recibo(**data_a_insertar))
                    next_numero_recibo += 1
                
                except KeyError as e:
                    # Este error ocurre si un encabezado falta, lo manejamos al final del try-except principal
                    raise KeyError(e) 
                
                except Exception as e:
                    # 📢 Este print te dirá qué está fallando exactamente en cada fila
                    print(f"ERROR DE VALIDACIÓN en fila {index + 5} (RIF: {rif_cedula_raw}): {e}")
                    total_errores += 1
                    # La fila es ignorada, y el bucle continúa

            # 4. Inserción Masiva
            if registros_a_crear:
                Recibo.objects.bulk_create(registros_a_crear)
            
            # 5. Retorno de Resultado
            mensaje_final = f"Se importaron {len(registros_a_crear)} recibos exitosamente."
            if total_errores > 0:
                mensaje_final += f" {total_errores} fila(s) fueron descartadas por errores de datos (revisar la consola del servidor)."
                
            return True, mensaje_final

    except KeyError as e:
        # Error al leer las columnas (falta un encabezado)
        return False, f"Error en la columna: La columna {e} no se encuentra en el archivo Excel. Revise la cabecera."
    except Exception as e:
        # Error general (archivo dañado, etc.)
        return False, f"Ocurrió un error inesperado durante la lectura del archivo: {str(e)}"