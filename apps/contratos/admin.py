from django.contrib import admin
from .models import Contrato, HistorialContrato, ConfiguracionInstitucional

@admin.register(ConfiguracionInstitucional)
class ConfiguracionInstitucionalAdmin(admin.ModelAdmin):
    # Esto hace que solo se vea una fila con los datos principales en la lista
    list_display = ('nombre_gerente', 'cedula_gerente', 'gaceta_nro', 'providencia_nro')
    
    # Evita que el usuario cree más de un registro si ya existe uno (opcional)
    def has_add_permission(self, request):
        if self.model.objects.count() >= 1:
            return False
        return super().has_add_permission(request)

@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ('codigo_contrato', 'beneficiario', 'estado', 'fecha_creacion')
    list_filter = ('estado', 'fecha_creacion')
    search_fields = ('codigo_contrato', 'beneficiario__nombre_completo', 'beneficiario__documento_identidad')

@admin.register(HistorialContrato)
class HistorialContratoAdmin(admin.ModelAdmin):
    list_display = ('contrato', 'accion', 'usuario', 'fecha')