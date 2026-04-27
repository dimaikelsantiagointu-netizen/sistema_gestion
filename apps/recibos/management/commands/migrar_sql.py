import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.timezone import make_aware
from django.db import transaction
from apps.recibos.models import Recibo

User = get_user_model()

class Command(BaseCommand):
    help = 'Migración de Recibos: Limpieza de montos sucios y sincronización de fechas'

    def add_arguments(self, parser):
        parser.add_argument('sql_file', type=str, help='Ruta al archivo .sql')

    def clean_decimal(self, value):
        """
        Limpia montos con formatos: '140', '30,00', '63.000,00' o 'X'
        """
        if not value or value == '\\N' or value.strip() == '' or value.strip().upper() == 'X':
            return Decimal('0.00')
        
        # Eliminamos espacios y puntos de miles, cambiamos coma por punto decimal
        clean_val = value.replace(' ', '').replace('.', '').replace(',', '.')
        
        try:
            # Si después de limpiar hay más de un punto (error de origen), tomamos el último
            if clean_val.count('.') > 1:
                parts = clean_val.split('.')
                clean_val = "".join(parts[:-1]) + "." + parts[-1]
            
            val = Decimal(clean_val)
            return val if val <= Decimal('999999999999999.99') else Decimal('0.00')
        except (InvalidOperation, ValueError):
            return Decimal('0.00')

    def parse_datetime_custom(self, value):
        if not value or value == '\\N' or value.strip() == '':
            return None
        try:
            # Maneja formatos con o sin microsegundos
            dt_str = value.split('.')[0]
            return make_aware(datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S'))
        except:
            try:
                # Intento por si solo viene la fecha
                return make_aware(datetime.strptime(value.strip(), '%Y-%m-%d'))
            except:
                return None

    def handle(self, *args, **options):
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(self.style.ERROR('Debe existir al menos un superusuario.'))
            return

        self.stdout.write(self.style.WARNING('>>> Iniciando migración de alta precisión...'))
        
        exitos = 0
        en_bloque = False

        with open(options['sql_file'], 'r', encoding='utf-8') as f:
            for linea in f:
                if 'COPY public.recibos_pago' in linea:
                    en_bloque = True
                    continue
                if en_bloque and linea.strip() == '\\.':
                    break
                
                if en_bloque:
                    cols = linea.replace('\n', '').split('\t')
                    if len(cols) < 20: continue

                    try:
                        # 1. Identificadores
                        num_recibo_raw = cols[1].strip()
                        num_recibo = int(num_recibo_raw) if num_recibo_raw.isdigit() else None
                        
                        # 2. Gestión de Fechas (CORREGIDO SEGÚN TU DATA)
                        # cols[22] es la fecha del recibo (ej: 2025-09-03)
                        # cols[25] es la fecha de creación en sistema (ej: 2025-11-06 14:49:07)
                        fecha_recibo_raw = cols[22] if cols[22] != '\\N' else None
                        
                        # Intentamos capturar la fecha de creación real del sistema
                        dt_creacion = None
                        if len(cols) > 25:
                            dt_creacion = self.parse_datetime_custom(cols[25])
                        
                        # Si no hay fecha de creación, usamos la del recibo
                        if not dt_creacion and fecha_recibo_raw:
                            dt_creacion = self.parse_datetime_custom(f"{fecha_recibo_raw} 00:00:00")

                        # 3. Limpieza de Transferencia
                        transf_raw = cols[20].strip()
                        num_transf = re.sub(r'[^0-9]', '', transf_raw)
                        if not num_transf or transf_raw.upper() in ['SI', 'NO', '\\N', 'S/N']:
                            num_transf = None

                        # 4. Procesamiento de Nombre y Estado
                        # Evitamos que se mezclen si vienen en la misma columna
                        nombre_raw = cols[3].strip().upper() if cols[3] != '\\N' else 'SIN NOMBRE'

                        # 5. Guardado Atómico
                        with transaction.atomic():
                            obj, created = Recibo.objects.update_or_create(
                                numero_recibo=num_recibo,
                                defaults={
                                    'estado': cols[2].strip().upper() if cols[2] != '\\N' else 'DESCONOCIDO',
                                    'nombre': nombre_raw,
                                    'rif_cedula_identidad': cols[4].strip().upper() if cols[4] != '\\N' else 'S/R',
                                    'direccion_inmueble': cols[5] if cols[5] != '\\N' else 'SIN DIRECCIÓN',
                                    'ente_liquidado': cols[6].strip().upper() if cols[6] != '\\N' else 'N/A',
                                    'gastos_administrativos': self.clean_decimal(cols[17]),
                                    'tasa_dia': self.clean_decimal(cols[18]),
                                    'total_monto_bs': self.clean_decimal(cols[19]),
                                    'numero_transferencia': num_transf,
                                    'conciliado': cols[21].lower() in ['t', 'true', '1', 'si'],
                                    'fecha': fecha_recibo_raw,
                                    'concepto': cols[23] if cols[23] != '\\N' else '',
                                    'usuario': admin_user,
                                    'anulado': cols[26].lower() == 't',
                                    'fecha_anulacion': self.parse_datetime_custom(cols[27]) if len(cols) > 27 else None,
                                }
                            )

                            # Bypass de auto_now_add para preservar la historia
                            if dt_creacion:
                                Recibo.objects.filter(pk=obj.pk).update(fecha_creacion=dt_creacion)

                        exitos += 1
                        if exitos % 500 == 0:
                            self.stdout.write(self.style.SUCCESS(f'>>> {exitos} registros procesados...'))

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error en fila {exitos+1} (Recibo {cols[1]}): {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f'\nNormalización terminada. {exitos} registros en base de datos.'))