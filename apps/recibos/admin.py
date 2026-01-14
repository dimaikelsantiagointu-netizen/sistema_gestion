from django.contrib import admin
from .models import Recibo
from django.core.exceptions import PermissionDenied

@admin.register(Recibo)
class ReciboAdmin(admin.ModelAdmin):
    list_display = ('numero_recibo', 'nombre', 'fecha', 'usuario', 'anulado')
    search_fields = ('numero_recibo', 'nombre')
    exclude = ('usuario',)

    # 1. VER TODOS: Eliminamos el filtro de queryset para que TODOS vean TODO
    def get_queryset(self, request):
        return super().get_queryset(request)

    # 2. AUTO-ASIGNACIÓN: Al crear uno nuevo, el dueño es el usuario actual
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.usuario = request.user
        super().save_model(request, obj, form, change)

    # 3. RESTRICCIÓN DE EDICIÓN: ¿Puede el usuario editar este registro específico?
    def has_change_permission(self, request, obj=None):
        # Si no hay objeto (lista general), se le permite entrar
        if obj is None:
            return True
        
        # Superusuarios y Admins pueden editar cualquiera
        if request.user.is_superuser or request.user.rol in ['admin', 'superadmin']:
            return True
        
        # El Usuario común SOLO puede editar si es el DUEÑO
        return obj.usuario == request.user

    # 4. RESTRICCIÓN DE BORRADO: Solo niveles altos
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.rol == 'superadmin'

    # 5. RESTRICCIÓN DE ANULACIÓN: Evitamos que usuarios comunes marquen "anulado" en registros ajenos
    def get_readonly_fields(self, request, obj=None):
        # Si el usuario común está viendo un recibo que NO es suyo:
        if obj and not (request.user.is_superuser or request.user.rol in ['admin', 'superadmin']):
            if obj.usuario != request.user:
                # Todos los campos serán de solo lectura (no podrá guardar cambios)
                return [f.name for f in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)