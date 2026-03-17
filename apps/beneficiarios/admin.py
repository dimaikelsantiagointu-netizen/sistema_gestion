from django.contrib import admin
from .models import Beneficiario

@admin.register(Beneficiario)
class BeneficiarioAdmin(admin.ModelAdmin):
    # 1. Configuración de la lista principal
    list_display = (
        'get_full_id', 
        'nombre_completo', 
        'genero', 
        'estado', 
        'municipio', 
        'discapacidad'
    )
    
    # 2. Filtros laterales para segmentar rápido
    list_filter = (
        'tipo_documento', 
        'genero', 
        'discapacidad', 
        'estado', 
        'municipio'
    )
    
    # 3. Campos de búsqueda (Cédula y Nombre)
    search_fields = ('documento_identidad', 'nombre_completo', 'email', 'telefono')
    
    # 4. Organización del formulario de edición en el Admin
    fieldsets = (
        ('Identificación Básica', {
            'fields': (('tipo_documento', 'documento_identidad'), 'nombre_completo', ('genero', 'discapacidad'))
        }),
        ('Información de Contacto', {
            'fields': ('telefono', 'email')
        }),
        ('Ubicación Geográfica', {
            'fields': ('estado', 'municipio', 'parroquia', 'ciudad', 'comuna', 'direccion_especifica')
        }),
    )

    # Función para mostrar el ID con el formato V-123456
    @admin.display(description='ID / Documento')
    def get_full_id(self, obj):
        return f"{obj.tipo_documento}-{obj.documento_identidad}"

    # Orden predeterminado (más recientes primero)
    ordering = ('-id',)