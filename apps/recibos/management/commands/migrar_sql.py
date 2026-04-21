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
    help = 'Migración de Recibos: Normalización total y preservación de fechas originales'

    def add_arguments(self, parser):
        parser.add_argument('sql_file', type=str, help='Ruta al archivo .sql')

    def clean_decimal(self, value):
        if not value or value == '\\N' or value.strip() == '':
            return Decimal('0.00')
        clean_val = value.replace(' ', '').replace('.', '').replace(',', '.')
        try:
            val = Decimal(clean_val)
            return val if val <= Decimal('999999999999999.99') else Decimal('0.00')
        except (InvalidOperation, ValueError):
            return Decimal('0.00')

    def parse_datetime_custom(self, value):
        if not value or value == '\\N':
            return None
        try:
            dt_str = value.split('.')[0]
            return make_aware(datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S'))
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
                        # 1. Preparación de Identificadores
                        num_recibo = int(cols[1]) if cols[1].isdigit() else None
                        
                        # 2. Manejo de Fechas (EL PUNTO CRÍTICO)
                        # cols[22] es la fecha del recibo (DateField)
                        # cols[x] buscaremos la fecha de creación original si existe en el SQL
                        # Si el SQL no tiene fecha_creacion, usaremos la misma del recibo para mantener coherencia
                        fecha_recibo_raw = cols[22] if cols[22] != '\\N' else None
                        dt_original = self.parse_datetime_custom(cols[22] + " 00:00:00") 

                        # 3. Limpieza de número de transferencia (Unicidad)
                        transf_raw = cols[20].strip()
                        num_transf = re.sub(r'[^0-9]', '', transf_raw)
                        if not num_transf or transf_raw.upper() in ['SI', 'NO', '\\N']:
                            num_transf = None
                        elif Recibo.objects.filter(numero_transferencia=num_transf).exclude(numero_recibo=num_recibo).exists():
                            num_transf = f"{num_transf}-{num_recibo}"

                        # 4. Creación/Actualización con Bypass de auto_now_add
                        with transaction.atomic():
                            obj, created = Recibo.objects.update_or_create(
                                numero_recibo=num_recibo,
                                defaults={
                                    'estado': cols[2].strip().upper() if cols[2] != '\\N' else 'DESCONOCIDO',
                                    'nombre': cols[3].strip().upper() if cols[3] != '\\N' else 'SIN NOMBRE',
                                    'rif_cedula_identidad': cols[4].strip().upper() if cols[4] != '\\N' else 'S/R',
                                    'direccion_inmueble': cols[5] if cols[5] != '\\N' else 'SIN DIRECCIÓN',
                                    'ente_liquidado': cols[6].strip().upper() if cols[6] != '\\N' else 'N/A',
                                    'categoria1': cols[7].lower() == 't',
                                    'categoria2': cols[8].lower() == 't',
                                    'categoria3': cols[9].lower() == 't',
                                    'categoria4': cols[10].lower() == 't',
                                    'categoria5': cols[11].lower() == 't',
                                    'categoria6': cols[12].lower() == 't',
                                    'categoria7': cols[13].lower() == 't',
                                    'categoria8': cols[14].lower() == 't',
                                    'categoria9': cols[15].lower() == 't',
                                    'categoria10': cols[16].lower() == 't',
                                    'gastos_administrativos': self.clean_decimal(cols[17]),
                                    'tasa_dia': self.clean_decimal(cols[18]),
                                    'total_monto_bs': self.clean_decimal(cols[19]),
                                    'numero_transferencia': num_transf,
                                    'conciliado': cols[21].lower() in ['t', 'true', '1'],
                                    'fecha': fecha_recibo_raw,
                                    'concepto': cols[23] if cols[23] != '\\N' else '',
                                    'usuario': admin_user,
                                    'anulado': cols[26].lower() == 't',
                                    'fecha_anulacion': self.parse_datetime_custom(cols[27]) if len(cols) > 27 else None,
                                }
                            )

                            # FORZADO DE FECHA DE AUDITORÍA:
                            # Usamos .update() porque salta el auto_now_add de Django
                            if dt_original:
                                Recibo.objects.filter(pk=obj.pk).update(fecha_creacion=dt_original)

                        exitos += 1
                        if exitos % 500 == 0:
                            self.stdout.write(self.style.SUCCESS(f'>>> {exitos} registros migrados...'))

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error en Recibo {cols[1]}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f'\nProceso finalizado. {exitos} registros normalizados.'))