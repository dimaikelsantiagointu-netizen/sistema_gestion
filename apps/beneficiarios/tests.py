from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Beneficiario, CategoriaVisita, Visita
from apps.territorio.models import Estado, Municipio, Parroquia


class CategoriaVisitaTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.superuser = user_model.objects.create_superuser(
            username='category-admin',
            password='test-password',
        )
        self.regular_user = user_model.objects.create_user(
            username='category-user',
            password='test-password',
        )

    def crear_beneficiario(self):
        estado = Estado.objects.create(nombre='Estado de prueba')
        municipio = Municipio.objects.create(nombre='Municipio de prueba', estado=estado)
        parroquia = Parroquia.objects.create(nombre='Parroquia de prueba', municipio=municipio)
        return Beneficiario.objects.create(
            documento_identidad='V-12345678',
            nombre_completo='Ciudadano de prueba',
            genero='M',
            estado=estado,
            municipio=municipio,
            parroquia=parroquia,
            direccion_especifica='Dirección de prueba',
        )

    def test_migration_seeds_current_categories_in_the_requested_order(self):
        names = list(
            CategoriaVisita.objects.filter(activa=True)
            .order_by('orden', 'nombre')
            .values_list('nombre', flat=True)
        )

        self.assertEqual(25, len(names))
        self.assertEqual('Atenciones AVV Técnicas y Jurídicas', names[0])
        self.assertEqual('Solicitud de Linderos', names[-1])
        self.assertEqual('CTU: Registro de CTU', names[5])
        self.assertEqual('CTU: Actualización de CTU', names[6])
        self.assertEqual('CTU: Corrección y asistencia jurídica al CTU', names[7])
        self.assertEqual('Regularización Comercial: Consignación de recaudos', names[8])
        self.assertEqual('Regularización Comercial: Inspección del local comercial', names[9])
        self.assertEqual('Regularización Comercial: Regularización comercial', names[10])

    def test_category_management_is_restricted_to_superusers(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse('beneficiarios:categorias_visita'))
        self.assertEqual(403, response.status_code)

        self.client.force_login(self.superuser)
        response = self.client.get(reverse('beneficiarios:categorias_visita'))
        self.assertEqual(200, response.status_code)

    def test_superuser_can_create_edit_and_delete_unused_category(self):
        self.client.force_login(self.superuser)
        response = self.client.post(
            reverse('beneficiarios:categoria_visita_crear'),
            {'nombre': 'Atención de prueba', 'orden': 26, 'activa': 'on'},
        )
        self.assertRedirects(response, reverse('beneficiarios:categorias_visita'))

        categoria = CategoriaVisita.objects.get(nombre='Atención de prueba')
        codigo_original = categoria.codigo
        response = self.client.post(
            reverse('beneficiarios:categoria_visita_editar', args=[categoria.pk]),
            {'nombre': 'Atención actualizada', 'orden': 27, 'activa': 'on'},
        )
        self.assertRedirects(response, reverse('beneficiarios:categorias_visita'))
        categoria.refresh_from_db()
        self.assertEqual('Atención actualizada', categoria.nombre)
        self.assertEqual(codigo_original, categoria.codigo)

        response = self.client.post(
            reverse('beneficiarios:categoria_visita_eliminar', args=[categoria.pk]),
        )
        self.assertRedirects(response, reverse('beneficiarios:categorias_visita'))
        self.assertFalse(CategoriaVisita.objects.filter(pk=categoria.pk).exists())

    def test_new_category_defaults_to_next_active_order_and_shifts_archived_rows(self):
        archived = CategoriaVisita.objects.create(
            nombre='Motivo histórico',
            orden=26,
            activa=False,
        )
        self.client.force_login(self.superuser)

        response = self.client.get(reverse('beneficiarios:categoria_visita_crear'))

        self.assertEqual(26, response.context['form'].fields['orden'].initial)
        response = self.client.post(
            reverse('beneficiarios:categoria_visita_crear'),
            {'nombre': 'Nueva categoría', 'orden': 26, 'activa': 'on'},
        )

        self.assertRedirects(response, reverse('beneficiarios:categorias_visita'))
        categoria = CategoriaVisita.objects.get(nombre='Nueva categoría')
        archived.refresh_from_db()
        self.assertEqual(26, categoria.orden)
        self.assertEqual(27, archived.orden)

    def test_visit_form_only_offers_active_categories(self):
        CategoriaVisita.objects.create(nombre='Categoría archivada', orden=100, activa=False)
        self.client.force_login(self.regular_user)

        response = self.client.get(reverse('beneficiarios:registrar_visita'))

        self.assertEqual(200, response.status_code)
        offered_categories = list(response.context['categorias'])
        self.assertTrue(offered_categories)
        self.assertTrue(all(categoria.activa for categoria in offered_categories))
        self.assertNotIn('Categoría archivada', [categoria.nombre for categoria in offered_categories])

    def test_category_with_visit_history_cannot_be_deleted(self):
        beneficiario = self.crear_beneficiario()
        categoria = CategoriaVisita.objects.get(codigo='atenciones_avv')
        visita = Visita.objects.create(
            beneficiario=beneficiario,
            categoria=categoria,
            descripcion='Visita de prueba',
        )
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse('beneficiarios:categoria_visita_eliminar', args=[categoria.pk]),
        )

        self.assertRedirects(response, reverse('beneficiarios:categorias_visita'))
        self.assertTrue(CategoriaVisita.objects.filter(pk=categoria.pk).exists())
        self.assertTrue(Visita.objects.filter(pk=visita.pk, categoria=categoria).exists())

    def test_register_visit_saves_selected_dynamic_category(self):
        beneficiario = self.crear_beneficiario()
        categoria = CategoriaVisita.objects.get(codigo='reunion')
        self.client.force_login(self.regular_user)

        response = self.client.post(reverse('beneficiarios:registrar_visita'), {
            'beneficiario_id': beneficiario.pk,
            'categoria': categoria.pk,
            'descripcion': 'Reunión de seguimiento',
        })

        self.assertRedirects(response, reverse('beneficiarios:detalle', args=[beneficiario.pk]))
        visita = Visita.objects.get(beneficiario=beneficiario)
        self.assertEqual(visita.categoria, categoria)

    def test_visit_delete_requires_post_and_preserves_history_on_get(self):
        beneficiario = self.crear_beneficiario()
        categoria = CategoriaVisita.objects.get(codigo='reunion')
        visita = Visita.objects.create(
            beneficiario=beneficiario,
            categoria=categoria,
            descripcion='Reunión de seguimiento',
        )
        self.client.force_login(self.superuser)
        url = reverse('beneficiarios:eliminar_visita', args=[visita.pk])

        response = self.client.get(url)

        self.assertEqual(405, response.status_code)
        self.assertTrue(Visita.objects.filter(pk=visita.pk).exists())

        response = self.client.post(url)

        self.assertRedirects(response, reverse('beneficiarios:detalle', args=[beneficiario.pk]))
        self.assertFalse(Visita.objects.filter(pk=visita.pk).exists())
