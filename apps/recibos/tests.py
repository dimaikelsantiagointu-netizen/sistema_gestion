import io
import pandas as pd
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.recibos.constants import CATEGORY_CHOICES
from apps.recibos.models import Recibo
from apps.recibos.utils import importar_recibos_desde_excel


class ReciboCategoryImportTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='tester', password='testpass123')

    def test_new_categories_are_available_in_catalog(self):
        category_keys = [key for key, _ in CATEGORY_CHOICES]
        self.assertIn('categoria11', category_keys)
        self.assertIn('categoria12', category_keys)
        self.assertIn('categoria13', category_keys)

    def test_import_from_excel_reads_new_category_columns(self):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            sheet = writer.book.create_sheet('Hoja2')
            header_row = [
                'estado', 'nombre', 'rif_cedula_identidad', 'direccion_inmueble', 'ente_liquidado',
                'categoria1', 'categoria2', 'categoria3', 'categoria4', 'categoria5',
                'categoria6', 'categoria7', 'categoria8', 'categoria9', 'categoria10',
                'categoria11', 'categoria12', 'categoria13',
                'gastos_administrativos', 'tasa_dia', 'total_monto_bs',
                'numero_transferencia', 'conciliado', 'fecha', 'concepto'
            ]
            sheet.append([''] * 4)
            sheet.append([''] * 4)
            sheet.append([''] * 4)
            sheet.append(header_row)
            sheet.append([
                'PENDIENTE', 'Juan Pérez', 'V12345678', 'Calle 1', 'INTU',
                'si', 'no', 'no', 'no', 'no',
                'no', 'no', 'no', 'no', 'no',
                'si', 'si', 'si',
                '100', '0.5', '100',
                'T001', 'si', '01/01/2025', 'Aclaratoria de prueba'
            ])
            for sheet_name in list(writer.book.sheetnames):
                if sheet_name != 'Hoja2':
                    writer.book.remove(writer.book[sheet_name])

        output.seek(0)
        uploaded = SimpleUploadedFile('recibos.xlsx', output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        success, message, pks = importar_recibos_desde_excel(uploaded, self.user)

        self.assertTrue(success, message)
        self.assertTrue(pks)
        recibo = Recibo.objects.get(pk=pks[0])
        self.assertTrue(recibo.categoria11)
        self.assertTrue(recibo.categoria12)
        self.assertTrue(recibo.categoria13)

    def test_import_from_excel_handles_header_on_later_row(self):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            sheet = writer.book.create_sheet('Hoja2')
            header_row = [
                'estado', 'nombre', 'rif_cedula_identidad', 'direccion_inmueble', 'ente_liquidado',
                'categoria1', 'categoria2', 'categoria3', 'categoria4', 'categoria5',
                'categoria6', 'categoria7', 'categoria8', 'categoria9', 'categoria10',
                'categoria11', 'categoria12', 'categoria13',
                'gastos_administrativos', 'tasa_dia', 'total_monto_bs',
                'numero_transferencia', 'conciliado', 'fecha', 'concepto'
            ]
            sheet.append(['nota', 'nota', 'nota', 'nota'])
            sheet.append(['nota', 'nota', 'nota', 'nota'])
            sheet.append(['nota', 'nota', 'nota', 'nota'])
            sheet.append(['nota', 'nota', 'nota', 'nota'])
            sheet.append(header_row)
            sheet.append([
                'PENDIENTE', 'Juan Pérez', 'V12345678', 'Calle 1', 'INTU',
                'si', 'no', 'no', 'no', 'no',
                'no', 'no', 'no', 'no', 'no',
                'si', 'si', 'si',
                '100', '0.5', '100',
                'T001', 'si', '01/01/2025', 'Aclaratoria de prueba'
            ])
            for sheet_name in list(writer.book.sheetnames):
                if sheet_name != 'Hoja2':
                    writer.book.remove(writer.book[sheet_name])

        output.seek(0)
        uploaded = SimpleUploadedFile('recibos.xlsx', output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        success, message, pks = importar_recibos_desde_excel(uploaded, self.user)

        self.assertTrue(success, message)
        self.assertEqual(len(pks), 1)

    def test_import_from_excel_maps_columns_by_header_name_when_order_changes(self):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            sheet = writer.book.create_sheet('Hoja2')
            header_row = [
                'numero_transferencia', 'conciliado', 'fecha', 'concepto',
                'estado', 'nombre', 'rif_cedula_identidad', 'direccion_inmueble', 'ente_liquidado',
                'categoria10', 'categoria11', 'categoria12', 'categoria13',
                'gastos_administrativos', 'tasa_dia', 'total_monto_bs',
                'categoria1', 'categoria2', 'categoria3', 'categoria4', 'categoria5',
                'categoria6', 'categoria7', 'categoria8', 'categoria9'
            ]
            sheet.append([''] * 4)
            sheet.append(header_row)
            sheet.append([
                'T001', 'si', '01/01/2025', 'Aclaratoria de prueba',
                'PENDIENTE', 'Juan Pérez', 'V12345678', 'Calle 1', 'INTU',
                'no', 'si', 'no', 'no',
                '100', '0.5', '100',
                'si', 'no', 'no', 'no', 'no',
                'no', 'no', 'no', 'no'
            ])
            for sheet_name in list(writer.book.sheetnames):
                if sheet_name != 'Hoja2':
                    writer.book.remove(writer.book[sheet_name])

        output.seek(0)
        uploaded = SimpleUploadedFile('recibos.xlsx', output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        success, message, pks = importar_recibos_desde_excel(uploaded, self.user)

        self.assertTrue(success, message)
        self.assertEqual(len(pks), 1)
        recibo = Recibo.objects.get(pk=pks[0])
        self.assertTrue(recibo.categoria1)
        self.assertFalse(recibo.categoria2)
        self.assertTrue(recibo.categoria11)
