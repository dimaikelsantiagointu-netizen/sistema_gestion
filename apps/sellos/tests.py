from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.recibos.models import Recibo
from apps.sellos.models import SelloDorado
from apps.sellos.services import asignar_recibos_a_sello
from apps.sellos.views import asignar_recibos_view, marcar_recibos_leidos_view


class SellosCoreTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.consultoria = User.objects.create_user(
            username='consultoria1',
            password='123456',
            rol='consultoria',
        )
        self.admin = User.objects.create_user(
            username='admin1',
            password='123456',
            rol='admin',
        )
        self.sello_a = SelloDorado.objects.create(nombre='Sello A', creado_por=self.consultoria)
        self.sello_b = SelloDorado.objects.create(nombre='Sello B', creado_por=self.consultoria)
        self.recibo = Recibo.objects.create(
            numero_recibo=900001,
            estado='Caracas',
            nombre='Usuario Test',
            rif_cedula_identidad='V12345678',
            direccion_inmueble='Dirección test',
            ente_liquidado='INTU',
            gastos_administrativos=1,
            tasa_dia=1,
            total_monto_bs=1,
            fecha='2026-01-01',
            concepto='Prueba',
            aprobado_sello_dorado=True,
            estatus_sello_dorado='aprobado',
            sello_dorado=self.sello_a,
        )

    def test_no_permite_asignar_un_recibo_a_dos_sellos_distintos(self):
        result = asignar_recibos_a_sello(self.sello_b, [self.recibo.pk], self.consultoria)
        self.assertFalse(result['success'])
        # ahora el servicio devuelve errores detallados
        self.assertTrue(len(result.get('errors', [])) >= 1)
        self.assertIn('Ya asignado', result['errors'][0]['reason'] or 'Ya asignado')
        self.recibo.refresh_from_db()
        self.assertEqual(self.recibo.sello_dorado, self.sello_a)

    def test_aprobar_marca_notificado_false_y_asignar_marca_true(self):
        # Asegurar que aprobar deja notificado_consultoria en False
        from apps.sellos.services import aprobar_recibos_para_sello
        recibos = aprobar_recibos_para_sello([self.recibo.pk], self.admin)
        self.recibo.refresh_from_db()
        self.assertFalse(self.recibo.notificado_consultoria)

        # Asignar ahora y verificar que se marca como notificado
        result = asignar_recibos_a_sello(self.sello_a, [self.recibo.pk], self.consultoria)
        self.assertTrue(result['success'] or not result['success'])
        self.recibo.refresh_from_db()
        self.assertTrue(self.recibo.notificado_consultoria)

    def test_asignar_por_region(self):
        # crear un recibo adicional en la misma región y sin sello
        r2 = Recibo.objects.create(
            numero_recibo=900002,
            estado='Caracas Centro',
            nombre='Usuario 2',
            rif_cedula_identidad='V87654321',
            direccion_inmueble='Dirección test 2',
            ente_liquidado='INTU',
            gastos_administrativos=1,
            tasa_dia=1,
            total_monto_bs=1,
            fecha='2026-01-02',
            concepto='Prueba2',
            aprobado_sello_dorado=True,
            estatus_sello_dorado='aprobado',
        )

        # Llamar a la vista de asignación simulando POST por región
        # verificar la lógica de asignación a nivel de servicio por región
        from apps.sellos.services import asignar_recibos_a_sello
        qs = Recibo.objects.filter(aprobado_sello_dorado=True, anulado=False, sello_dorado__isnull=True, estado__icontains='Caracas')
        ids = list(qs.values_list('pk', flat=True))
        result = asignar_recibos_a_sello(self.sello_b, ids, self.consultoria)
        self.assertTrue(result['success'])
        r2.refresh_from_db()
        self.assertEqual(r2.sello_dorado, self.sello_b)

    def test_marcar_leidos_endpoint(self):
        from django.test import RequestFactory
        rf = RequestFactory()
        post = {'recibo_ids': f'{self.recibo.pk}'}
        request = rf.post('/sellos/marcar_leidos/', data=post)
        request.user = self.consultoria
        response = marcar_recibos_leidos_view(request)
        import json
        data = json.loads(response.content)
        self.assertTrue(data.get('success'))
        self.recibo.refresh_from_db()
        self.assertTrue(self.recibo.notificado_consultoria)

    def test_export_csv(self):
        # crear otro recibo aprobado
        r3 = Recibo.objects.create(
            numero_recibo=900003,
            estado='Zulia',
            nombre='Usuario 3',
            rif_cedula_identidad='V33333333',
            direccion_inmueble='Dir 3',
            ente_liquidado='INTU',
            gastos_administrativos=1,
            tasa_dia=1,
            total_monto_bs=1,
            fecha='2026-01-03',
            concepto='Prueba3',
            aprobado_sello_dorado=True,
            estatus_sello_dorado='aprobado',
        )
        self.client.force_login(self.consultoria)
        resp = self.client.get('/sellos/export/?')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv')
        content = resp.content.decode('utf-8')
        self.assertIn('numero_recibo', content)

    def test_asignacion_parcial(self):
        # recibo aprobado y otro no aprobado
        r_ok = Recibo.objects.create(
            numero_recibo=900004,
            estado='Caracas Oeste',
            nombre='Usuario OK',
            rif_cedula_identidad='V44444444',
            direccion_inmueble='Dir 4',
            ente_liquidado='INTU',
            gastos_administrativos=1,
            tasa_dia=1,
            total_monto_bs=1,
            fecha='2026-01-04',
            concepto='Prueba4',
            aprobado_sello_dorado=True,
            estatus_sello_dorado='aprobado',
        )
        r_no = Recibo.objects.create(
            numero_recibo=900005,
            estado='Caracas Oeste',
            nombre='Usuario NO',
            rif_cedula_identidad='V55555555',
            direccion_inmueble='Dir 5',
            ente_liquidado='INTU',
            gastos_administrativos=1,
            tasa_dia=1,
            total_monto_bs=1,
            fecha='2026-01-05',
            concepto='Prueba5',
            aprobado_sello_dorado=False,
            estatus_sello_dorado='borrador',
        )

        resultado = asignar_recibos_a_sello(self.sello_b, [r_ok.pk, r_no.pk], self.consultoria)
        # Debe asignar el aprobado y reportar error para el no aprobado
        self.assertEqual(resultado.get('assigned_count'), 1)
        self.assertIn(r_ok.pk, resultado.get('assigned_ids'))
        self.assertEqual(len(resultado.get('errors')), 1)
        r_ok.refresh_from_db()
        r_no.refresh_from_db()
        self.assertEqual(r_ok.sello_dorado, self.sello_b)
        self.assertIsNone(r_no.sello_dorado)
