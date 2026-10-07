from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse


class UserRoleViewTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username='root-admin',
            email='root@example.com',
            password='test-password',
        )
        self.client.force_login(self.admin)

    def test_create_superadmin_sets_superuser_flags(self):
        response = self.client.post(reverse('users:crear_usuario'), {
            'username': 'new-superadmin',
            'first_name': 'New',
            'last_name': 'Admin',
            'email': 'new-admin@example.com',
            'telefono': '',
            'rol': 'superadmin',
            'observacion': '',
            'password1': 'Valid-Test-Password-123!',
            'password2': 'Valid-Test-Password-123!',
        })

        self.assertRedirects(response, reverse('home'))
        user = get_user_model().objects.get(username='new-superadmin')
        self.assertEqual('superadmin', user.rol)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_updating_role_to_superadmin_sets_superuser_flags(self):
        user = get_user_model().objects.create_user(
            username='promoted-user',
            email='promoted@example.com',
            password='test-password',
        )

        response = self.client.post(reverse('users:usuario_editar', args=[user.pk]), {
            'username': user.username,
            'first_name': 'Promoted',
            'last_name': 'User',
            'email': user.email,
            'telefono': '',
            'rol': 'superadmin',
            'observacion': '',
            'password': '',
        })

        self.assertRedirects(response, reverse('users:usuario_list'))
        user.refresh_from_db()
        self.assertEqual('superadmin', user.rol)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_contracts_permission_shows_dashboard_link(self):
        user = get_user_model().objects.create_user(
            username='contracts-user',
            email='contracts@example.com',
            password='test-password',
        )
        permission = Permission.objects.get(
            content_type__app_label='users',
            codename='ver_gestor_contratos',
        )
        user.user_permissions.add(permission)
        self.client.force_login(user)

        response = self.client.get(reverse('home'))

        self.assertEqual(200, response.status_code)
        self.assertContains(response, reverse('contratos:lista'))
