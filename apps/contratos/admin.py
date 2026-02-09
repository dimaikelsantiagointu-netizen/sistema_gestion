from django.contrib import admin
from .models import Contrato, ConfiguracionInstitucional

@admin.register(ConfiguracionInstitucional)
class ConfiguracionInstitucionalAdmin(admin.ModelAdmin):
    list_display = ('nombre_gerente', 'cedula_gerente', 'gaceta_nro', 'providencia_nro')
    
    def has_add_permission(self, request):
        if self.model.objects.count() >= 1:
            return False
        return super().has_add_permission(request)

@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ('codigo_contrato', 'get_beneficiarios', 'estado', 'fecha_creacion')
    
    def get_beneficiarios(self, obj):
        return ", ".join([b.nombre_completo for b in obj.beneficiarios.all()])
    
    get_beneficiarios.short_description = 'Beneficiarios'
