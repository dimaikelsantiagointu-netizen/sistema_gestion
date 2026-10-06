import base64
import io
import re
import zlib
from datetime import date
from decimal import Decimal

import pandas as pd
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.recibos.constants import CATEGORY_CHOICES
from apps.recibos.forms import ReciboForm
from apps.recibos.models import Recibo
from apps.recibos.utils import (
    generar_pdf_recibo_unitario,
    importar_recibos_desde_excel,
    limpiar_y_convertir_decimal,
)


class ReciboCategoryImportTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='tester', password='testpass123')

    def test_decimal_conversion_handles_european_thousands_and_decimal_separators(self):
        self.assertEqual(Decimal('1234.56'), limpiar_y_convertir_decimal('1.234,56'))

    def test_editing_recibo_preserves_existing_receipt_number_when_not_submitted(self):
        recibo = Recibo.objects.create(
            numero_recibo=12345,
            estado='MIRANDA',
            nombre='Juan Pérez',
            rif_cedula_identidad='V12345678',
            direccion_inmueble='Calle 1',
            ente_liquidado='INTU',
            gastos_administrativos=Decimal('10.00'),
            tasa_dia=Decimal('0.5000'),
            total_monto_bs=Decimal('10.00'),
            fecha=date(2025, 1, 1),
            concepto='Concepto inicial',
        )

        form = ReciboForm(
            data={
                'estado': 'MIRANDA',
                'nombre': 'Juan Pérez',
                'rif_cedula_identidad': 'V12345678',
                'direccion_inmueble': 'Calle 1',
                'ente_liquidado': 'INTU',
                'gastos_administrativos': '10.00',
                'tasa_dia': '0.5000',
                'total_monto_bs': '10.00',
                'numero_transferencia': '',
                'fecha': '2025-01-01',
                'concepto': 'Concepto actualizado',
            },
            instance=recibo,
        )

        self.assertTrue(form.is_valid(), form.errors)
        saved_recibo = form.save()

        self.assertEqual(saved_recibo.numero_recibo, 12345)
        self.assertEqual(saved_recibo.concepto, 'Concepto actualizado')

    def test_new_categories_are_available_in_catalog(self):
        category_keys = [key for key, _ in CATEGORY_CHOICES]
        self.assertIn('categoria11', category_keys)
        self.assertIn('categoria12', category_keys)
        self.assertIn('categoria13', category_keys)
        self.assertIn('categoria14', category_keys)
        self.assertEqual(
            '14. Ventas y Operaciones Comerciales',
            dict(CATEGORY_CHOICES)['categoria14'],
        )
        self.assertIn('categoria14', ReciboForm().fields)

    def test_category_14_is_saved_and_counted_as_a_category(self):
        recibo = Recibo.objects.create(
            estado='MIRANDA',
            nombre='Juan Pérez',
            rif_cedula_identidad='V12345678',
            direccion_inmueble='Calle 1',
            ente_liquidado='INTU',
            categoria14=True,
            gastos_administrativos=Decimal('10.00'),
            tasa_dia=Decimal('0.5000'),
            total_monto_bs=Decimal('10.00'),
            fecha=date(2025, 1, 1),
            concepto='Venta',
        )

        self.assertTrue(recibo.categoria14)
        self.assertTrue(recibo.tiene_categorias())

    def test_sales_category_pdf_uses_professional_title_and_description(self):
        recibo = Recibo.objects.create(
            estado='MIRANDA',
            nombre='Juan Pérez',
            rif_cedula_identidad='V12345678',
            direccion_inmueble='Calle 1',
            ente_liquidado='INTU',
            categoria14=True,
            gastos_administrativos=Decimal('10.00'),
            tasa_dia=Decimal('0.5000'),
            total_monto_bs=Decimal('10.00'),
            fecha=date(2025, 1, 1),
            concepto='Venta',
        )

        pdf_response = generar_pdf_recibo_unitario(recibo)
        pdf_streams = re.findall(rb'stream\r?\n(.*?)endstream', pdf_response.content, re.DOTALL)
        pdf_content = []
        for stream in pdf_streams:
            try:
                stream = base64.a85decode(b'<~' + stream.strip(), adobe=True)
            except ValueError:
                pass
            try:
                pdf_content.append(zlib.decompress(stream))
            except zlib.error:
                pdf_content.append(stream)
        pdf_text = b'\n'.join(pdf_content)

        self.assertIn(b'VENTAS Y OPERACIONES COMERCIALES', pdf_text)
        self.assertIn(b'Registro del pago asociado a una', pdf_text)

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

    def test_import_from_excel_reads_sales_category_and_shifted_columns(self):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            sheet = writer.book.create_sheet('Hoja2')
            header_row = [
                'estado', 'nombre', 'rif_cedula_identidad', 'direccion_inmueble', 'ente_liquidado',
                'categoria1', 'categoria2', 'categoria3', 'categoria4', 'categoria5',
                'categoria6', 'categoria7', 'categoria8', 'categoria9', 'categoria10',
                'categoria11', 'categoria12', 'categoria13', '10.- Venta',
                'Gastos Admin (Bs)', 'Tasa BCV', 'Monto Total (Bs)', 'Referencia Bancaria',
                '¿Conciliado?', 'Fecha de Pago', 'Concepto del Pago',
            ]
            sheet.append([''] * 4)
            sheet.append(header_row)
            sheet.append([
                'PENDIENTE', 'María Pérez', 'V87654321', 'Av. Principal', 'INTU',
                'no', 'no', 'no', 'no', 'no', 'no', 'no', 'no', 'no', 'no',
                'no', 'no', 'no', 'si', '125.50', '36.5', '133.25',
                'TRXVENTA14', 'no', '29/09/2025', 'Venta comercial',
            ])
            for sheet_name in list(writer.book.sheetnames):
                if sheet_name != 'Hoja2':
                    writer.book.remove(writer.book[sheet_name])

        output.seek(0)
        uploaded = SimpleUploadedFile(
            'recibos_ventas.xlsx',
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

        success, message, pks = importar_recibos_desde_excel(uploaded, self.user)

        self.assertTrue(success, message)
        recibo = Recibo.objects.get(pk=pks[0])
        self.assertTrue(recibo.categoria14)
        self.assertEqual(recibo.gastos_administrativos, Decimal('125.50'))
        self.assertEqual(recibo.tasa_dia, Decimal('36.5000'))
        self.assertEqual(recibo.total_monto_bs, Decimal('133.25'))
        self.assertEqual(recibo.numero_transferencia, 'TRXVENTA14')
        self.assertEqual(recibo.fecha, date(2025, 9, 29))
        self.assertEqual(recibo.concepto, 'Venta Comercial')

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
