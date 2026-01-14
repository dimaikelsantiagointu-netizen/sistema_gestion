# apps/users/management/commands/setup_roles.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    help = 'Configura los grupos y permisos iniciales'

    def handle(self, *args, **options):
        # 1. Crear Grupo Administrador
        admin_group, created = Group.objects.get_or_create(name='Administradores')
        
        # 2. Crear Grupo Usuario (Lectura)
        user_group, created = Group.objects.get_or_create(name='Usuarios_Lectura')

        self.stdout.write(self.style.SUCCESS('Grupos creados exitosamente'))