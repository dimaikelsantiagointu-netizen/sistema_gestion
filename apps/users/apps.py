# apps/users/apps.py
from django.apps import AppConfig

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users' # Verifica que este sea el path correcto de tu app

    def ready(self):
        # Esta línea es la "llave" que activa las señales
        import apps.users.models