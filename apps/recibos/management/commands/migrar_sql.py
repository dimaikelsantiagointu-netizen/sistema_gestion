import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.timezone import make_aware
from django.db import transaction, IntegrityError
from apps.recibos.models import Recibo

User = get_user_model()

class Command(BaseCommand):
    help = 'Migración de Recibos: Integridad Total y Carga sin Pérdida'

    def add_arguments(self, parser):
        parser.add_argument('sql_file', type=str, help='Ruta al archivo .sql')

    def clean_decimal(self, value):
        if not value or value == '\\N' or value.strip() == '' or value.strip().upper() == 'X':
            return Decimal('0.00')
        
        raw_val = value.strip().replace(' ', '')
        # Si tiene punto y coma, es formato europeo/latino (1.234,56)
        if ',' in raw_val and '.' in raw_val:
            clean_val = raw_val.replace('.', '').replace(',', '.')
        # Si solo tiene coma, es el decimal (73431,13)
        elif ',' in raw_val:
            clean_val = raw_val.replace(',', '.')
        # Si tiene un punto y no es separador de miles (73431.13)
        else:
            clean_val = raw_val

        try:
            return Decimal(clean_val)
        except (InvalidOperation, ValueError):
            return Decimal('0.00')

    def parse_datetime_custom(self, value):
        if not value or value == '\\N' or value.strip() == '':
            return None
        value = value.strip()
        
        formatos = [
            '%Y-%m-%d %H:%M:%S.%f', # Con microsegundos
            '%Y-%m-%d %H:%M:%S',    # Estándar
            '%Y-%m-%d',             # Solo fecha
        ]
        
        for formato in formatos:
            try:
                dt = datetime.strptime(value, formato)
                return make_aware(dt)
            except (ValueError, TypeError):
                continue
        return None

    def handle(self, *args, **options):
        admin_user = User.objects.filter(is_superuser=True).first()
        self.stdout.write(self.style.WARNING('>>> Iniciando carga de integridad total...'))
        
        total_lineas = 0
        exitos = 0
        errores = 0
        en_bloque = False

        with open(options['sql_file'], 'r', encoding='utf-8') as f:
            for linea in f:
                if 'COPY public.recibos_pago' in linea:
                    en_bloque = True
                    continue
                if en_bloque and (linea.strip() == '\\.' or linea.startswith('setval')):
                    en_bloque = False
                    break
                
                if en_bloque:
                    total_lineas += 1
                    cols = linea.replace('\n', '').split('\t')
                    
                    # Verificación de integridad de columnas (basado en tu dump)
                    if len(cols) < 29:
                        self.stdout.write(self.style.ERROR(f"Línea {total_lineas} incompleta (Columnas: {len(cols)})"))
                        errores += 1
                        continue

                    try:
                        # --- EXTRACCIÓN DE DATOS ---
                        num_recibo = cols[1].strip()
                        if not num_recibo.isdigit():
                            continue
                        
                        # Fechas: La clave para no fusionarlas es tomarlas crudas primero
                        fecha_raw = cols[22].strip() # fecha
                        creacion_raw = cols[25].strip() # fecha_creacion
                        anulacion_raw = cols[27].strip() if len(cols) > 27 else None

                        dt_fecha = self.parse_datetime_custom(fecha_raw)
                        dt_creacion = self.parse_datetime_custom(creacion_raw)
                        dt_anulacion = self.parse_datetime_custom(anulacion_raw)

                        # Transferencia con sufijo para evitar colisiones de unicidad
                        num_transf = re.sub(r'[^0-9]', '', cols[20])
                        if num_transf:
                            if Recibo.objects.filter(numero_transferencia=num_transf).exclude(numero_recibo=num_recibo).exists():
                                num_transf = f"{num_transf}-{num_recibo}"
                        else:
                            num_transf = None

                        # --- GUARDADO ---
                        # Usamos update_or_create para no duplicar si el script corre dos veces
                        obj, created = Recibo.objects.update_or_create(
                            numero_recibo=num_recibo,
                            defaults={
                                'estado': cols[2].strip().upper(),
                                'nombre': cols[3].strip().upper()[:255],
                                'rif_cedula_identidad': cols[4].strip().upper(),
                                'direccion_inmueble': cols[5].strip(),
                                'ente_liquidado': cols[6].strip().upper(),
                                'categoria1': cols[7].strip().lower() == 't',
                                'categoria2': cols[8].strip().lower() == 't',
                                'categoria3': cols[9].strip().lower() == 't',
                                'categoria4': cols[10].strip().lower() == 't',
                                'categoria5': cols[11].strip().lower() == 't',
                                'categoria6': cols[12].strip().lower() == 't',
                                'categoria7': cols[13].strip().lower() == 't',
                                'categoria8': cols[14].strip().lower() == 't',
                                'categoria9': cols[15].strip().lower() == 't',
                                'categoria10': cols[16].strip().lower() == 't',
                                'gastos_administrativos': self.clean_decimal(cols[17]),
                                'tasa_dia': self.clean_decimal(cols[18]),
                                'total_monto_bs': self.clean_decimal(cols[19]),
                                'numero_transferencia': num_transf,
                                'conciliado': cols[21].strip().upper() == 'SI',
                                'fecha': dt_fecha.date() if dt_fecha else None,
                                'concepto': cols[23].strip(),
                                'usuario': admin_user,
                                'anulado': cols[26].lower() == 't',
                                'fecha_anulacion': dt_anulacion,
                            }
                        )

                        # Forzar fecha de creación histórica (evita que Django ponga 'hoy')
                        if dt_creacion:
                            Recibo.objects.filter(pk=obj.pk).update(fecha_creacion=dt_creacion)
                        
                        exitos += 1

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error en Recibo {cols[1]}: {str(e)}"))
                        errores += 1

                    if total_lineas % 500 == 0:
                        self.stdout.write(f">>> Procesadas {total_lineas} líneas...")

        self.stdout.write(self.style.SUCCESS(
            f'\nRESUMEN FINAL:\n'
            f'- Líneas leídas: {total_lineas}\n'
            f'- Éxitos: {exitos}\n'
            f'- Errores: {errores}'
        ))