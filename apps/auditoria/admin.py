from django.contrib import admin
from .models import LogAuditoria

@admin.register(LogAuditoria)
class AuditoriaAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'usuario', 'modulo', 'accion', 'direccion_ip')
    readonly_fields = [f.name for f in LogAuditoria._meta.get_fields()] # Todo solo lectura
    
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False