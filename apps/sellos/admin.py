from django.contrib import admin
from .models import HistorialSello, SelloDorado
from apps.recibos.models import Recibo


class ReciboInline(admin.TabularInline):
	model = Recibo
	fields = ('numero_recibo', 'nombre', 'estado', 'estatus_sello_dorado', 'aprobado_sello_dorado', 'notificado_consultoria')
	readonly_fields = ('numero_recibo', 'nombre', 'estado', 'estatus_sello_dorado', 'aprobado_sello_dorado', 'notificado_consultoria')
	extra = 0
	can_delete = False
	show_change_link = True


@admin.register(SelloDorado)
class SelloDoradoAdmin(admin.ModelAdmin):
	list_display = ('codigo_sello', 'estado', 'fecha_creacion', 'get_recibos_count', 'get_recibos_aprobados')
	list_filter = ('estado', 'fecha_creacion')
	search_fields = ('codigo_sello',)
	inlines = [ReciboInline]

	def get_recibos_count(self, obj):
		return obj.recibo_set.count()
	get_recibos_count.short_description = 'Recibos totales'

	def get_recibos_aprobados(self, obj):
		return obj.recibo_set.filter(aprobado_sello_dorado=True).count()
	get_recibos_aprobados.short_description = 'Recibos aprobados'


admin.site.register(HistorialSello)
