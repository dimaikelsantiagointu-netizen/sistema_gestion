from django.contrib import admin
from django.apps import AppConfig
from .models import (
    Region, Estado, Municipio, Parroquia, Ciudad, 
    UnidadTrabajo, Empleado, BienNacional, MovimientoBien
)

# Configuración básica para tablas geográficas
@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)

@admin.register(Estado)
class EstadoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'region')
    list_filter = ('region',)
    search_fields = ('nombre',)

@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'estado')
    list_filter = ('estado__region', 'estado')
    search_fields = ('nombre',)
    
@admin.register(Parroquia)
class ParroquiaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'municipio')
    list_filter = ('municipio__estado', 'municipio')
    search_fields = ('nombre',)

@admin.register(Ciudad)
class CiudadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'estado')
    list_filter = ('estado',)
    search_fields = ('nombre',)

@admin.register(UnidadTrabajo)
class UnidadTrabajoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ciudad', 'parroquia')
    search_fields = ('nombre', 'direccion')
    list_filter = ('ciudad__estado', 'ciudad')

@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('cedula', 'nombre', 'apellido', 'cargo', 'unidad_trabajo', 'estatus')
    search_fields = ('cedula', 'nombre', 'apellido')
    list_filter = ('estatus', 'unidad_trabajo')

# CONFIGURACIÓN AVANZADA PARA BIENES NACIONALES
@admin.register(BienNacional)
class BienNacionalAdmin(admin.ModelAdmin):
    # Columnas que verás en la lista principal
    list_display = ('nro_identificacion', 'descripcion', 'marca', 'serial', 'estado_bien', 'empleado_uso', 'monto')
    
    # Buscador potente (puedes buscar por ID, Serial o nombre del empleado)
    search_fields = ('nro_identificacion', 'serial', 'descripcion', 'empleado_uso__nombre', 'empleado_uso__cedula')
    
    # Filtros laterales para auditoría rápida
    list_filter = ('estado_bien', 'unidad_trabajo', 'fecha_registro')
    
    # Campos de solo lectura para evitar errores manuales
    readonly_fields = ('uuid', 'qr_imagen', 'fecha_registro')
    
    # Organización del formulario de edición por secciones
    fieldsets = (
        ('Identificación Principal', {
            'fields': ('nro_identificacion', 'uuid', 'qr_imagen')
        }),
        ('Especificaciones Técnicas', {
            'fields': ('descripcion', 'marca', 'modelo', 'color', 'serial', 'estado_bien')
        }),
        ('Valores y Ubicación', {
            'fields': ('monto', 'unidad_trabajo', 'empleado_uso')
        }),
        ('Auditoría Institucional', {
            'fields': ('responsable_patrimonial', 'jefe_inventariado', 'registro_persona', 'observaciones')
        }),
    )

@admin.register(MovimientoBien)
class MovimientoBienAdmin(admin.ModelAdmin):
    list_display = ('bien', 'empleado_anterior', 'empleado_nuevo', 'fecha', 'usuario_sistema')
    list_filter = ('fecha', 'usuario_sistema')
    readonly_fields = ('fecha',)
    
    
class BienesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.bienes'

    def ready(self):
        import apps.bienes.signals