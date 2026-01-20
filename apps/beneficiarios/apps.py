from django.apps import AppConfig

class BeneficiariosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.beneficiarios'  # <--- Debe incluir el prefijo 'apps.'