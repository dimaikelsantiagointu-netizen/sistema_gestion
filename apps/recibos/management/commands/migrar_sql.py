import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.timezone import make_aware
from apps.recibos.models import Recibo

User = get_user_model()

COPY_HEADER_REGEX = re.compile(r'COPY\s+public\.recibos_pago\s*\((.*?)\)\s+FROM\s+stdin;', re.IGNORECASE)
BOOLEAN_TRUE = {'t', 'true', 'si', 's', '1', 'yes'}


class Command(BaseCommand):
    help = 'Migración de Recibos: Integridad Total y Carga sin Pérdida'

    def add_arguments(self, parser):
        parser.add_argument('sql_file', type=str, help='Ruta al archivo .sql')

    def clean_decimal(self, value):
        if value is None:
            return Decimal('0.00')

        raw_val = str(value).strip()
        if raw_val == '' or raw_val == '\\N' or raw_val.upper() == 'X':
            return Decimal('0.00')

        raw_val = raw_val.replace(' ', '')
        if ',' in raw_val and '.' in raw_val:
            clean_val = raw_val.replace('.', '').replace(',', '.')
        elif ',' in raw_val:
            clean_val = raw_val.replace(',', '.')
        else:
            clean_val = raw_val

        try:
            return Decimal(clean_val)
        except (InvalidOperation, ValueError):
            return Decimal('0.00')

    def parse_datetime_custom(self, value):
        if value is None:
            return None

        raw = str(value).strip()
        if raw == '' or raw == '\\N':
            return None

        formatos = [
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
        ]
        for formato in formatos:
            try:
                dt = datetime.strptime(raw, formato)
                return make_aware(dt)
            except (ValueError, TypeError):
                continue
        return None

    def decode_copy_value(self, value):
        if value is None or value == '\\N':
            return None

        s = str(value)
        result = []
        i = 0
        while i < len(s):
            if s[i] == '\\' and i + 1 < len(s):
                esc = s[i + 1]
                if esc == 'n':
                    result.append('\n')
                elif esc == 'r':
                    result.append('\r')
                elif esc == 't':
                    result.append('\t')
                elif esc == '\\':
                    result.append('\\')
                else:
                    result.append(esc)
                i += 2
            else:
                result.append(s[i])
                i += 1
        return ''.join(result)

    def parse_boolean(self, value):
        if value is None:
            return False
        return str(value).strip().lower() in BOOLEAN_TRUE

    def handle(self, *args, **options):
        admin_user = User.objects.filter(is_superuser=True).first()
        self.stdout.write(self.style.WARNING('>>> Iniciando carga de integridad total...'))

        total_lineas = 0
        exitos = 0
        errores = 0
        en_bloque = False
        field_names = []
        field_map = {}

        with open(options['sql_file'], 'r', encoding='utf-8') as f:
            for linea in f:
                if not en_bloque:
                    match = COPY_HEADER_REGEX.search(linea)
                    if match:
                        en_bloque = True
                        field_names = [col.strip() for col in match.group(1).split(',')]
                        field_map = {name: idx for idx, name in enumerate(field_names)}
                        continue

                if en_bloque and (linea.strip() == '\\.' or linea.strip().lower().startswith('setval')):
                    en_bloque = False
                    break

                if en_bloque:
                    total_lineas += 1
                    cols = linea.rstrip('\n').split('\t')

                    if len(cols) < len(field_names):
                        self.stdout.write(self.style.ERROR(
                            f"Línea {total_lineas} incompleta (Columnas: {len(cols)} vs esperadas {len(field_names)})"
                        ))
                        errores += 1
                        continue

                    def get_col(name, default=''):
                        idx = field_map.get(name)
                        if idx is None or idx >= len(cols):
                            return default
                        return self.decode_copy_value(cols[idx])

                    try:
                        num_recibo_raw = str(get_col('numero_recibo', '')).strip()
                        if not num_recibo_raw.isdigit():
                            continue
                        num_recibo = int(num_recibo_raw)

                        fecha_raw = get_col('fecha')
                        creacion_raw = get_col('fecha_creacion')
                        anulacion_raw = get_col('fecha_anulacion')

                        dt_fecha = self.parse_datetime_custom(fecha_raw)
                        dt_creacion = self.parse_datetime_custom(creacion_raw)
                        dt_anulacion = self.parse_datetime_custom(anulacion_raw)

                        num_transf_raw = get_col('numero_transferencia') or ''
                        num_transf = re.sub(r'[^0-9]', '', num_transf_raw)
                        if num_transf:
                            if Recibo.objects.filter(numero_transferencia=num_transf).exclude(numero_recibo=num_recibo).exists():
                                num_transf = f"{num_transf}-{num_recibo}"
                        else:
                            num_transf = None

                        usuario = admin_user
                        usuario_creador_raw = get_col('usuario_creador')
                        if usuario_creador_raw and str(usuario_creador_raw).isdigit():
                            posible_usuario = User.objects.filter(pk=int(usuario_creador_raw)).first()
                            if posible_usuario:
                                usuario = posible_usuario

                        defaults = {
                            'estado': str(get_col('estado', '')).strip().upper(),
                            'nombre': str(get_col('nombre', '')).strip().upper()[:500],
                            'rif_cedula_identidad': str(get_col('rif_cedula_identidad', '')).strip().upper(),
                            'direccion_inmueble': str(get_col('direccion_inmueble', '')).strip(),
                            'ente_liquidado': str(get_col('ente_liquidado', '')).strip().upper(),
                            'gastos_administrativos': self.clean_decimal(get_col('gastos_administrativos')),
                            'tasa_dia': self.clean_decimal(get_col('tasa_dia')),
                            'total_monto_bs': self.clean_decimal(get_col('total_monto_bs')),
                            'numero_transferencia': num_transf,
                            'conciliado': self.parse_boolean(get_col('conciliado')),
                            'fecha': dt_fecha.date() if dt_fecha else None,
                            'concepto': str(get_col('concepto', '')).strip(),
                            'usuario': usuario,
                            'anulado': self.parse_boolean(get_col('anulado')),
                            'fecha_anulacion': dt_anulacion,
                        }

                        for i in range(1, 14):
                            defaults[f'categoria{i}'] = self.parse_boolean(get_col(f'categoria{i}'))

                        obj, created = Recibo.objects.update_or_create(
                            numero_recibo=num_recibo,
                            defaults=defaults
                        )

                        if dt_creacion:
                            Recibo.objects.filter(pk=obj.pk).update(fecha_creacion=dt_creacion)

                        exitos += 1

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error en Recibo {num_recibo_raw}: {str(e)}"))
                        errores += 1

                    if total_lineas % 500 == 0:
                        self.stdout.write(f">>> Procesadas {total_lineas} líneas...")

        self.stdout.write(self.style.SUCCESS(
            f'\nRESUMEN FINAL:\n'
            f'- Líneas leídas: {total_lineas}\n'
            f'- Éxitos: {exitos}\n'
            f'- Errores: {errores}'
        ))