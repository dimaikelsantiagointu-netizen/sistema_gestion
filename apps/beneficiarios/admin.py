from django.contrib import admin
from .models import Beneficiario

@admin.register(Beneficiario)
class BeneficiarioAdmin(admin.ModelAdmin):
    # 1. Configuración de la lista principal (Agregamos fecha_nacimiento)
    list_display = (
        'get_full_id', 
        'nombre_completo', 
        'fecha_nacimiento', # <--- Nuevo
        'genero', 
        'estado', 
        'discapacidad'
    )
    
    # 2. Filtros laterales
    list_filter = (
        'tipo_documento', 
        'genero', 
        'discapacidad', 
        'estado', 
        'fecha_nacimiento' # <--- Permite filtrar por años/meses
    )
    
    # 3. Campos de búsqueda
    search_fields = ('documento_identidad', 'nombre_completo', 'email', 'telefono')
    
    # 4. Organización del formulario de edición (AQUÍ ES DONDE SE ACTIVA EN EL FORM)
    fieldsets = (
        ('Identificación Básica', {
            'fields': (
                ('tipo_documento', 'documento_identidad'), 
                'nombre_completo', 
                'fecha_nacimiento', # <--- Lo añadimos aquí
                ('genero', 'discapacidad')
            )
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

    # Orden predeterminado
    ordering = ('-id',)