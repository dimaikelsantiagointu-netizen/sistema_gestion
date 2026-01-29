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
    # Cambiamos 'beneficiario' por una función personalizada 'get_beneficiarios'
    list_display = ('codigo_contrato', 'get_beneficiarios', 'estado', 'fecha_creacion')
    
    def get_beneficiarios(self, obj):
        # Esto concatena los nombres para que se vean en la lista del admin
        return ", ".join([b.nombre_completo for b in obj.beneficiarios.all()])
    
    get_beneficiarios.short_description = 'Beneficiarios'
@admin.register(HistorialContrato)
class HistorialContratoAdmin(admin.ModelAdmin):
    list_display = ('contrato', 'accion', 'usuario', 'fecha')