from django.contrib import admin
from .models import Personal, DocumentoPersonal

# ==============================================================================
# 1. CONFIGURACIÓN DE DOCUMENTOS (COMO FILAS DENTRO DEL TRABAJADOR)
# ==============================================================================
class DocumentoPersonalInline(admin.TabularInline):
    model = DocumentoPersonal
    extra = 1  # Permite añadir un documento vacío al final
    fields = ('nombre_documento', 'categoria', 'archivo', 'fecha_subida')
    readonly_fields = ('fecha_subida',)

# ==============================================================================
# 2. CONFIGURACIÓN DEL TRABAJADOR
# ==============================================================================
@admin.register(Personal)
class PersonalAdmin(admin.ModelAdmin):
    # Columnas visibles en el listado principal
    list_display = ('cedula', 'apellidos', 'nombres', 'cargo', 'unidad_adscrita', 'activo')
    
    # Filtros laterales
    list_filter = ('activo', 'unidad_adscrita', 'cargo')
    
    # Buscador superior
    search_fields = ('cedula', 'apellidos', 'nombres')
    
    # Orden predeterminado
    ordering = ('apellidos',)
    
    # Agrupación de campos en el formulario de edición
    fieldsets = (
        ('Información Personal', {
            'fields': (('nombres', 'apellidos'), 'cedula')
        }),
        ('Información Laboral', {
            'fields': ('cargo', 'unidad_adscrita', 'fecha_ingreso', 'activo')
        }),
    )
    
    # Insertamos la gestión de documentos dentro de la vista de Personal
    inlines = [DocumentoPersonalInline]

# ==============================================================================
# 3. REGISTRO INDEPENDIENTE DE DOCUMENTOS (OPCIONAL)
# ==============================================================================
@admin.register(DocumentoPersonal)
class DocumentoPersonalAdmin(admin.ModelAdmin):
    list_display = ('nombre_documento', 'personal', 'categoria', 'fecha_subida')
    list_filter = ('categoria', 'fecha_subida')
    search_fields = ('nombre_documento', 'personal__cedula', 'personal__apellidos')