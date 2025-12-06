from django.apps import AppConfig

class RecibosConfig(AppConfig):
    # El nombre completo del módulo Python para la aplicación
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.recibos'
    # La etiqueta corta (ej. 'recibos') para referencias como las migraciones
    label = 'recibos'