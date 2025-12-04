from django.contrib import admin
from .models import Receipt

# Customización para mostrar campos específicos en la lista del admin
class ReceiptAdmin(admin.ModelAdmin):
    """
    Define cómo se verá el modelo Receipt en el panel de administración de Django.
    """
    # Campos a mostrar en la lista de recibos
    list_display = ('receipt_number', 'client_name', 'client_id', 'amount', 'payment_date', 'status', 'created_by')
    # Campos por los que se puede buscar
    search_fields = ('receipt_number', 'client_name', 'client_id', 'transaction_number')
    # Filtros laterales
    list_filter = ('status', 'payment_date', 'created_by')
    # Campos de solo lectura
    readonly_fields = ('created_at', 'created_by')
    
    # Define la estructura de los formularios de edición
    fieldsets = (
        ('Información del Recibo', {
            'fields': ('receipt_number', 'status', 'amount', 'transaction_number', 'payment_date', 'concept'),
        }),
        ('Datos del Cliente', {
            'fields': ('client_name', 'client_id', 'client_address'),
        }),
        ('Categorías (Regularización)', {
            'fields': ('categoria1', 'categoria2', 'categoria3', 'categoria4', 'categoria5', 'categoria6', 'categoria7', 'categoria8', 'categoria9', 'categoria10'),
            'classes': ('collapse',), # Oculta las categorías por defecto
        }),
        ('Auditoría', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',),
        }),
    )


# Registra el modelo Receipt con la configuración personalizada
admin.site.register(Receipt, ReceiptAdmin)