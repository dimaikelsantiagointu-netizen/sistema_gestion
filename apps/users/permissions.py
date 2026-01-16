# apps/users/permissions.py
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied

class AdminRequiredMixin(UserPassesTestMixin):
    """Solo permite el acceso si es Superusuario o tiene rol Administrador"""
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.rol == 'admin'

class UserRequiredMixin(UserPassesTestMixin):
    """Permite el acceso a cualquier usuario autenticado con rol de lectura"""
    def test_func(self):
        return self.request.user.is_authenticated