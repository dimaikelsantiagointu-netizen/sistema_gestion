# apps/users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario

class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'rol', 'is_staff', 'is_superuser')
    
    # Esto permite que los permisos se vean mejor en el admin
    filter_horizontal = ('groups', 'user_permissions') 
    
    fieldsets = UserAdmin.fieldsets + (
        ('Configuración de Acceso', {'fields': ('rol',)}),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Configuración de Acceso', {'fields': ('rol',)}),
    )

# Si ya estaba registrado, lo quitamos para evitar errores de duplicado
if admin.site.is_registered(Usuario):
    admin.site.unregister(Usuario)

admin.site.register(Usuario, UsuarioAdmin)