from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.territorio.models import Comuna, Estado, Municipio, Parroquia

from .forms import ExpedienteForm, MultiplePDFField
from .models import EstatusDocumento, Expediente, Titular


class GestionDocumentalTests(TestCase):
    def setUp(self):
        self.estado = Estado.objects.create(nombre='Estado de prueba')
        self.otro_estado = Estado.objects.create(nombre='Otro estado')
        self.municipio = Municipio.objects.create(
            nombre='Municipio de prueba',
            estado=self.estado,
        )
        self.otro_municipio = Municipio.objects.create(
            nombre='Municipio ajeno',
            estado=self.otro_estado,
        )
        self.parroquia = Parroquia.objects.create(
            nombre='Parroquia de prueba',
            municipio=self.municipio,
        )
        self.comuna = Comuna.objects.create(
            nombre='Comuna de prueba',
            parroquia=self.parroquia,
        )
        self.titular = Titular.objects.create(nombre='Titular de prueba')
        self.estatus = EstatusDocumento.objects.create(nombre='Estatus de prueba')

    def crear_usuario_con_permisos_catalogos(self, username, rol):
        user = get_user_model().objects.create_user(
            username=username,
            password='test-password',
            rol=rol,
        )
        permissions = Permission.objects.filter(
            content_type__app_label='users',
            codename__in=[
                'ver_gestor_documental',
                'gestionar_catalogos_documentales',
            ],
        )
        user.user_permissions.add(*permissions)
        return user

    def crear_expediente(self, **overrides):
        values = {
            'estado': self.estado,
            'municipio': self.municipio,
            'parroquia': self.parroquia,
            'comuna': self.comuna,
            'titular': self.titular,
            'numero_protocolo': 'PROTO-1',
            'numero_tomo': 'TOMO-1',
            'superficie_m2': Decimal('12500.00'),
            'direccion': 'Dirección de prueba',
            'lindero_norte': 'Norte',
            'lindero_sur': 'Sur',
            'lindero_este': 'Este',
            'lindero_oeste': 'Oeste',
            'estatus': self.estatus,
        }
        values.update(overrides)
        return Expediente(**values)

    def test_code_sequence_is_continuous_and_hectares_are_calculated(self):
        first = self.crear_expediente()
        first.save()
        second = self.crear_expediente()
        second.save()

        self.assertRegex(first.codigo, r'^EXP-\d{4}-000001$')
        self.assertRegex(second.codigo, r'^EXP-\d{4}-000002$')
        self.assertEqual(Decimal('1.2500'), first.superficie_hectareas)

    def test_rejects_municipality_from_another_state(self):
        expediente = self.crear_expediente(municipio=self.otro_municipio)

        with self.assertRaises(ValidationError) as error:
            expediente.full_clean()

        self.assertIn('municipio', error.exception.message_dict)

    def test_edit_form_keeps_current_inactive_catalog_values_selectable(self):
        expediente = self.crear_expediente()
        expediente.save()
        self.titular.activo = False
        self.titular.save()
        self.estatus.activo = False
        self.estatus.save()
        Titular.objects.create(nombre='Otro titular inactivo', activo=False)
        EstatusDocumento.objects.create(nombre='Otro estatus inactivo', activo=False)

        form = ExpedienteForm(instance=expediente)

        self.assertTrue(
            form.fields['titular'].queryset.filter(pk=self.titular.pk).exists(),
        )
        self.assertFalse(
            form.fields['titular'].queryset.exclude(pk=self.titular.pk).filter(
                activo=False,
            ).exists(),
        )
        self.assertTrue(
            form.fields['estatus'].queryset.filter(pk=self.estatus.pk).exists(),
        )
        self.assertFalse(
            form.fields['estatus'].queryset.exclude(pk=self.estatus.pk).filter(
                activo=False,
            ).exists(),
        )

    def test_pdf_field_rejects_oversized_and_non_pdf_uploads(self):
        field = MultiplePDFField(required=False)
        oversized_pdf = SimpleUploadedFile(
            'large.pdf',
            b'%PDF-' + b'x' * (5 * 1024 * 1024),
            content_type='application/pdf',
        )
        invalid_pdf = SimpleUploadedFile(
            'not-a-pdf.pdf',
            b'not a PDF',
            content_type='application/pdf',
        )

        with self.assertRaises(ValidationError):
            field.clean([oversized_pdf])
        with self.assertRaises(ValidationError):
            field.clean([invalid_pdf])

    def test_module_pages_render_and_access_requires_permission(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username='document-user',
            password='test-password',
        )
        self.client.force_login(user)
        self.assertEqual(
            403,
            self.client.get(reverse('gestion_documental:dashboard')).status_code,
        )

        admin = user_model.objects.create_superuser(
            username='document-admin',
            email='document-admin@example.com',
            password='test-password',
        )
        self.client.force_login(admin)
        expediente = self.crear_expediente()
        expediente.save()
        urls = [
            reverse('gestion_documental:dashboard'),
            reverse('gestion_documental:lista'),
            reverse('gestion_documental:crear'),
            reverse('gestion_documental:detalle', args=[expediente.pk]),
            reverse('gestion_documental:editar', args=[expediente.pk]),
            reverse('gestion_documental:titulares'),
            reverse('gestion_documental:crear_titular'),
            reverse('gestion_documental:estatus'),
            reverse('gestion_documental:crear_estatus'),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(200, response.status_code)
                self.assertContains(
                    response,
                    'aria-label="Regresar al centro de control"',
                )

        dashboard_response = self.client.get(
            reverse('gestion_documental:dashboard'),
        )
        self.assertNotContains(
            dashboard_response,
            reverse('auditoria:ver_bitacora'),
        )
        self.assertContains(
            self.client.get(reverse('home')),
            reverse('auditoria:ver_bitacora'),
        )

    def test_invalid_date_range_does_not_show_unfiltered_records(self):
        admin = get_user_model().objects.create_superuser(
            username='date-filter-admin',
            email='date-filter-admin@example.com',
            password='test-password',
        )
        self.client.force_login(admin)
        expediente = self.crear_expediente()
        expediente.save()

        response = self.client.get(
            reverse('gestion_documental:dashboard'),
            {'fecha_desde': '2025-02-02', 'fecha_hasta': '2025-02-01'},
        )

        self.assertEqual(0, response.context['total_expedientes'])
        self.assertContains(response, 'La fecha final debe ser posterior a la inicial.')

    def test_regular_catalog_manager_can_view_but_not_modify_statuses(self):
        user = self.crear_usuario_con_permisos_catalogos(
            'regular-catalog-user',
            'user',
        )
        self.client.force_login(user)

        list_response = self.client.get(reverse('gestion_documental:estatus'))
        self.assertEqual(200, list_response.status_code)
        self.assertNotContains(
            list_response,
            reverse('gestion_documental:crear_estatus'),
        )
        self.assertNotContains(
            list_response,
            reverse('gestion_documental:editar_estatus', args=[self.estatus.pk]),
        )
        self.assertEqual(
            403,
            self.client.get(reverse('gestion_documental:crear_estatus')).status_code,
        )
        self.assertEqual(
            403,
            self.client.post(
                reverse('gestion_documental:editar_estatus', args=[self.estatus.pk]),
                {'nombre': 'Cambio no autorizado', 'orden': 1, 'activo': 'on'},
            ).status_code,
        )
        self.assertEqual(
            403,
            self.client.post(
                reverse('gestion_documental:eliminar_estatus', args=[self.estatus.pk]),
            ).status_code,
        )
        self.estatus.refresh_from_db()
        self.assertEqual('Estatus de prueba', self.estatus.nombre)

    def test_admin_can_delete_only_unreferenced_statuses(self):
        admin = self.crear_usuario_con_permisos_catalogos(
            'catalog-admin',
            'admin',
        )
        self.client.force_login(admin)
        unused_status = EstatusDocumento.objects.create(nombre='Estatus sin uso')

        response = self.client.post(
            reverse('gestion_documental:eliminar_estatus', args=[unused_status.pk]),
        )
        self.assertRedirects(response, reverse('gestion_documental:estatus'))
        self.assertFalse(
            EstatusDocumento.objects.filter(pk=unused_status.pk).exists(),
        )

        expediente = self.crear_expediente()
        expediente.save()
        response = self.client.post(
            reverse('gestion_documental:eliminar_estatus', args=[self.estatus.pk]),
            follow=True,
        )
        self.assertContains(
            response,
            'No se puede eliminar este estatus porque tiene expedientes asociados.',
        )
        self.assertTrue(EstatusDocumento.objects.filter(pk=self.estatus.pk).exists())

    def test_expedientes_list_defaults_to_ten_and_accepts_page_size_choices(self):
        admin = get_user_model().objects.create_superuser(
            username='pagination-admin',
            email='pagination-admin@example.com',
            password='test-password',
        )
        self.client.force_login(admin)
        for index in range(12):
            self.crear_expediente(numero_protocolo=f'PROTO-{index}').save()

        list_url = reverse('gestion_documental:lista')
        response = self.client.get(list_url)
        self.assertTrue(
            response.context['filtros'].is_valid(),
            response.context['filtros'].errors,
        )
        self.assertEqual(10, response.context['pagina'].paginator.per_page)
        self.assertEqual(10, len(response.context['pagina']))
        self.assertContains(response, '?per_page=10&amp;page=2')

        second_page = self.client.get(
            list_url,
            {'per_page': '10', 'page': '2'},
        )
        self.assertEqual(2, len(second_page.context['pagina']))

        custom_page_size = self.client.get(list_url, {'per_page': '25'})
        self.assertEqual(25, custom_page_size.context['pagina'].paginator.per_page)
        self.assertEqual(12, len(custom_page_size.context['pagina']))

        invalid_page_size = self.client.get(list_url, {'per_page': '1000'})
        self.assertEqual(10, invalid_page_size.context['pagina'].paginator.per_page)
        self.assertContains(
            invalid_page_size,
            'El tamaño debe ser uno de 10, 25, 50, 100.',
        )
