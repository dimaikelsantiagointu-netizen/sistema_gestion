from django.contrib import admin

from .models import ArchivoExpediente, EstatusDocumento, Expediente, Titular


class ArchivoExpedienteInline(admin.TabularInline):
    model = ArchivoExpediente
    extra = 0
    readonly_fields = ('fecha_subida',)


@admin.register(Expediente)
class ExpedienteAdmin(admin.ModelAdmin):
    list_display = (
        'codigo',
        'titular',
        'estado',
        'estatus',
        'fecha_registro',
        'superficie_m2',
    )
    list_filter = ('estado', 'estatus', 'fecha_registro')
    search_fields = (
        'codigo',
        'titular__nombre',
        'titular__documento_identidad',
        'numero_protocolo',
        'numero_tomo',
    )
    readonly_fields = ('codigo', 'fecha_creacion', 'fecha_actualizacion')
    inlines = [ArchivoExpedienteInline]


@admin.register(Titular)
class TitularAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'documento_identidad', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre', 'documento_identidad')


@admin.register(EstatusDocumento)
class EstatusDocumentoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'orden', 'activo')
    list_filter = ('activo',)
    ordering = ('orden', 'nombre')
