import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.timezone import make_aware
from apps.recibos.models import Recibo

User = get_user_model()

class Command(BaseCommand):
    help = 'Versión Final Pro: Migración con bypass de duplicados y protección de desbordamiento'

    def add_arguments(self, parser):
        parser.add_argument('sql_file', type=str, help='Ruta al archivo .sql')

    def clean_decimal(self, value):
        """Limpia y protege contra números que desbordan el campo numeric(19,4)"""
        if not value or value == '\\N' or value.strip() == '':
            return Decimal('0.00')
        
        clean_val = value.replace(' ', '').replace('.', '').replace(',', '.')
        
        try:
            val_decimal = Decimal(clean_val)
            if val_decimal.is_infinite() or val_decimal > Decimal('999999999999999.9999'):
                return Decimal('0.00')
            return val_decimal
        except (InvalidOperation, ValueError):
            return Decimal('0.00')

    def normalizar_estado(self, nombre_estado):
        if not nombre_estado or nombre_estado == '\\N':
            return "DESCONOCIDO"
        estado = nombre_estado.strip().upper()
        remplazos_acentos = {'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U'}
        for original, reemplazo in remplazos_acentos.items():
            estado = estado.replace(original, reemplazo)
        if "DTO.CAPITAL" in estado or "DTTO.CAPITAL" in estado: return "DISTRITO CAPITAL"
        if "ZULA" == estado: return "ZULIA"
        if estado.startswith("S/D"): return None
        return estado

    def handle(self, *args, **options):
        sql_file_path = options['sql_file']
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user, _ = User.objects.get_or_create(username='admin', defaults={'is_staff': True, 'is_superuser': True})

        self.stdout.write(self.style.WARNING('Iniciando migración final...'))
        exitos = 0
        errores = 0
        en_bloque_datos = False

        with open(sql_file_path, 'r', encoding='utf-8') as f:
            for linea in f:
                if 'COPY public.recibos_pago' in linea:
                    en_bloque_datos = True
                    continue
                if en_bloque_datos and linea.strip() == '\\.':
                    en_bloque_datos = False
                    break
                
                if en_bloque_datos:
                    columnas = linea.replace('\n', '').split('\t')
                    if len(columnas) < 20: continue

                    try:
                        estado_limpio = self.normalizar_estado(columnas[2])
                        if estado_limpio is None: continue

                        # 1. Montos con protección de desbordamiento
                        gastos = self.clean_decimal(columnas[17])
                        tasa = self.clean_decimal(columnas[18])
                        total = self.clean_decimal(columnas[19])
                        num_recibo_int = int(columnas[1]) if columnas[1].isdigit() else None

                        # 2. Control de Unicidad Transferencia
                        raw_transf = columnas[20].strip()
                        val_transf = re.sub(r'[^0-9]', '', raw_transf)
                        
                        if not val_transf or raw_transf.upper() in ['SI', 'NO', 'S/N', '\\N']:
                            val_transf = None
                        else:
                            # Bypass de duplicados
                            if Recibo.objects.filter(numero_transferencia=val_transf).exclude(numero_recibo=num_recibo_int).exists():
                                val_transf = f"{val_transf}-{num_recibo_int}"

                        # 3. Fechas
                        fecha_anulacion = None
                        if len(columnas) > 27 and columnas[27] != '\\N':
                            try:
                                dt_str = columnas[27].split('.')[0]
                                dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
                                fecha_anulacion = make_aware(dt)
                            except: pass

                        # 4. Guardar o Actualizar
                        Recibo.objects.update_or_create(
                            numero_recibo=num_recibo_int,
                            defaults={
                                'estado': estado_limpio,
                                'nombre': columnas[3].strip().upper() if columnas[3] != '\\N' else 'SIN NOMBRE',
                                'rif_cedula_identidad': columnas[4].strip().upper() if columnas[4] != '\\N' else 'S/R',
                                'direccion_inmueble': columnas[5] if columnas[5] != '\\N' else 'SIN DIRECCION',
                                'ente_liquidado': columnas[6].strip().upper() if columnas[6] != '\\N' else 'N/A',
                                'categoria1': columnas[7].lower() == 't',
                                'categoria2': columnas[8].lower() == 't',
                                'categoria3': columnas[9].lower() == 't',
                                'categoria4': columnas[10].lower() == 't',
                                'categoria5': columnas[11].lower() == 't',
                                'categoria6': columnas[12].lower() == 't',
                                'categoria7': columnas[13].lower() == 't',
                                'categoria8': columnas[14].lower() == 't',
                                'categoria9': columnas[15].lower() == 't',
                                'categoria10': columnas[16].lower() == 't',
                                'gastos_administrativos': gastos,
                                'tasa_dia': tasa,
                                'total_monto_bs': total,
                                'numero_transferencia': val_transf,
                                'conciliado': 'SI' in raw_transf.upper() or columnas[21].lower() in ['t', 'true', '1', 'si'],
                                'fecha': columnas[22] if columnas[22] != '\\N' else None,
                                'concepto': columnas[23] if columnas[23] != '\\N' else '',
                                'usuario': admin_user,
                                'anulado': columnas[26].lower() == 't',
                                'fecha_anulacion': fecha_anulacion
                            }
                        )
                        exitos += 1
                        if exitos % 500 == 0:
                            self.stdout.write(self.style.SUCCESS(f'>>> {exitos} procesados...'))
                            
                    except Exception as e:
                        errores += 1
                        self.stdout.write(self.style.ERROR(f"Error Recibo {columnas[1]}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f'\n {exitos} registros migrados.'))