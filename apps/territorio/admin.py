from django.contrib import admin
from .models import Estado, Municipio, Ciudad, Parroquia, Comuna, UnidadAdscrita

@admin.register(Estado)
class EstadoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)
    ordering = ('nombre',)

@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'estado')
    list_filter = ('estado',)
    search_fields = ('nombre',)
    ordering = ('estado', 'nombre')

@admin.register(Ciudad)
class CiudadAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'estado')
    list_filter = ('estado',)
    search_fields = ('nombre',)
    ordering = ('estado', 'nombre')

@admin.register(Parroquia)
class ParroquiaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'get_estado', 'municipio')
    list_filter = ('municipio__estado', 'municipio')
    search_fields = ('nombre',)
    ordering = ('municipio', 'nombre')

    # Método para mostrar el Estado en la lista de Parroquias
    @admin.display(description='Estado', ordering='municipio__estado')
    def get_estado(self, obj):
        return obj.municipio.estado.nombre

@admin.register(Comuna)
class ComunaAdmin(admin.ModelAdmin):
    list_select_related = ('parroquia__municipio',)
    list_display = ('id', 'nombre', 'parroquia', 'get_municipio')
    list_filter = ('parroquia__municipio__estado', 'parroquia__municipio')
    search_fields = ('nombre',) 
    ordering = ('parroquia', 'nombre')

    @admin.display(description='Municipio', ordering='parroquia__municipio')
    def get_municipio(self, obj):
        return obj.parroquia.municipio.nombre

@admin.register(UnidadAdscrita)
class UnidadAdscritaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'descripcion', 'total_personal')
    search_fields = ('nombre',)
    ordering = ('nombre',)

