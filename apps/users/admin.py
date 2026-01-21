# apps/users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario

class UsuarioAdmin(UserAdmin):
    # 1. Campos que se ven en la tabla principal (list_display)
    # Eliminamos 'cedula' y agregamos 'rol' y 'telefono' para mejor visibilidad
    list_display = ('username', 'email', 'rol', 'telefono', 'is_staff')
    
    # 2. Filtros laterales para facilitar la búsqueda
    list_filter = ('rol', 'is_staff', 'is_superuser', 'is_active')

    # 3. Campos al editar un usuario existente
    # Agregamos 'observacion' y quitamos 'cedula'
    fieldsets = UserAdmin.fieldsets + (
        ('Información Personal Extra', {'fields': ('telefono', 'observacion')}),
        ('Configuración de Sistema', {'fields': ('rol',)}),
    )
    
    # 4. Campos al crear un usuario nuevo desde el Admin
    # Agregamos 'observacion' y quitamos 'cedula'
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información Extra', {'fields': ('rol', 'telefono', 'observacion')}),
    )

    # Ordenar por nombre de usuario por defecto
    ordering = ('username',)

admin.site.register(Usuario, UsuarioAdmin)