# apps/users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario

class UsuarioAdmin(UserAdmin):
    # Campos que se ven en la tabla principal
    list_display = ('username', 'cedula', 'rol', 'is_staff', 'is_superuser')
    
    # Campos al editar un usuario
    fieldsets = UserAdmin.fieldsets + (
        ('Información Personal Extra', {'fields': ('cedula', 'telefono')}),
        ('Configuración de Sistema', {'fields': ('rol',)}),
    )
    
    # Campos al crear un usuario nuevo
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información Extra', {'fields': ('cedula', 'telefono', 'rol')}),
    )

admin.site.register(Usuario, UsuarioAdmin)