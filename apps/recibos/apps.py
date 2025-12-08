from django.apps import AppConfig

# El nombre de la clase DEBE coincidir con lo que tienes en settings.py
class RecibosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.recibos' 
    # ^ Asegúrate de que 'name' coincida con la ruta de tu aplicación