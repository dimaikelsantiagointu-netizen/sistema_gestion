from django.contrib import admin
from django.utils.html import format_html
from .models import LogAuditoria
import json

@admin.register(LogAuditoria)
class AuditoriaAdmin(admin.ModelAdmin):
    # 1. Configuración de la lista principal
    list_display = ('get_timestamp', 'usuario', 'modulo', 'get_accion_badge', 'direccion_ip', 'short_description')
    list_filter = ('accion', 'modulo', 'timestamp', ('usuario', admin.RelatedOnlyFieldListFilter))
    search_fields = ('usuario__username', 'modulo', 'descripcion', 'direccion_ip', 'objeto_id')
    date_hierarchy = 'timestamp' # Barra de navegación temporal superior
    
    # 2. Bloqueo total de edición (Inmutabilidad)
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

    # 3. Organización del formulario de detalle (Readonly)
    readonly_fields = ('timestamp', 'usuario', 'modulo', 'accion', 'direccion_ip', 
                       'objeto_id', 'descripcion', 'pretty_valor_anterior', 'pretty_valor_nuevo')
    
    fieldsets = (
        ('Información del Evento', {
            'fields': ('timestamp', 'usuario', 'direccion_ip')
        }),
        ('Detalles de la Operación', {
            'fields': ('modulo', 'accion', 'objeto_id', 'descripcion')
        }),
        ('Trazabilidad de Datos (Metadatos)', {
            'fields': ('pretty_valor_anterior', 'pretty_valor_nuevo'),
            'classes': ('collapse',), # Colapsable para no saturar la vista
        }),
    )

    # --- MÉTODOS DE ESTILO Y FORMATO ---

    def get_timestamp(self, obj):
        return obj.timestamp.strftime('%d/%m/%Y %H:%M:%S')
    get_timestamp.short_description = 'Fecha y Hora'
    get_timestamp.admin_order_field = 'timestamp'

    def get_accion_badge(self, obj):
        """ Colores para identificar acciones rápidamente """
        colors = {
            'C': '#10b981', # Verde (Creación)
            'M': '#3b82f6', # Azul (Modificación)
            'E': '#ef4444', # Rojo (Eliminación)
            'L': '#8b5cf6', # Morado (Login)
            'S': '#6b7280', # Gris (Logout)
            'F': '#f59e0b', # Naranja (Fallo)
        }
        color = colors.get(obj.accion, '#000000')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 12px; font-weight: bold; font-size: 10px;">{}</span>',
            color, obj.get_accion_display()
        )
    get_accion_badge.short_description = 'Acción'

    def short_description(self, obj):
        return obj.descripcion[:60] + "..." if len(obj.descripcion) > 60 else obj.descripcion
    short_description.short_description = 'Resumen'

    def pretty_json(self, data):
        """ Renderiza el JSON de forma legible en el admin """
        if not data:
            return "Sin datos"
        # Convertimos el diccionario a un string JSON formateado con indentación
        pretty = json.dumps(data, indent=4, ensure_ascii=False)
        return format_html('<pre style="background: #f8f9fa; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">{}</pre>', pretty)

    def pretty_valor_anterior(self, obj):
        return self.pretty_json(obj.valor_anterior)
    pretty_valor_anterior.short_description = "Estado Anterior"

    def pretty_valor_nuevo(self, obj):
        return self.pretty_json(obj.valor_nuevo)
    pretty_valor_nuevo.short_description = "Estado Nuevo"