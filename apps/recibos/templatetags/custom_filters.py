# recibos/templatetags/custom_filters.py
from django import template
from django.utils.text import slugify as django_slugify
from django.template.defaultfilters import capfirst
from ..models import CATEGORY_CHOICES_MAP
from urllib.parse import urlencode
import re
# 💡 NOTA IMPORTANTE:
# Debes reemplazar el siguiente diccionario de ejemplo 
# con la importación real de tu mapeo de categorías desde models.py.
register = template.Library()
# Ejemplo de cómo debe lucir el mapeo:
CATEGORY_CHOICES_MAP = {
    1: 'Pago Mensual',
    2: 'Alquiler',
    3: 'Servicios Básicos',
    4: 'Mantenimiento',
    5: 'Suministros',
    6: 'Impuestos',
    7: 'Viáticos',
    8: 'Comisiones',
    9: 'Publicidad',
    10: 'Otros Gastos',
}
# La forma correcta de importarlo sería:
# from ..models import CATEGORY_CHOICES_MAP  # Si está en models.py

register = template.Library()


@register.filter
def slugify(value):
    """
    Convierte el valor a un 'slug' amigable para URL/ID, 
    utilizando la función interna de Django.
    Usado en el HTML para generar IDs limpios para los checkboxes de filtro.
    Ej: "Pago Mensual" -> "pago-mensual"
    """
    return django_slugify(value)


@register.filter
def get_category_label(field_name):
    """
    Toma la clave numérica de la categoría (1, 2, 3...) y 
    devuelve la etiqueta legible asociada.
    Esto es útil para mostrar el nombre de la categoría en la tabla de resultados.
    """
    if not field_name:
        return ""
    
    return CATEGORY_CHOICES_MAP.get(field_name, 'Concepto Desconocido')

@register.filter(name='get_item')
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter(name='remove_page')
def remove_page(url_querystring):
    """Elimina 'page' de la query string para que se pueda añadir un nuevo número de página."""
    return re.sub(r'[?&]page=\d+', '', url_querystring)