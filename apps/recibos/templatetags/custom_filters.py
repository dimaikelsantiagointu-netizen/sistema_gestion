from django import template
from django.utils.text import slugify as django_slugify
from django.template.defaultfilters import capfirst
from ..models import CATEGORY_CHOICES_MAP  
from urllib.parse import urlparse, parse_qs, urlencode
import re

register = template.Library()

# --- FILTROS DE MANEJO DE CADENAS Y LISTAS ---

@register.filter
def split(value, arg):
    """
    Divide una cadena (value) por un delimitador (arg).
    Uso en template: 'cadena,con,comas'|split:','
    Necesario para iterar sobre tamaños de página y categorías en listas de cadenas.
    """
    try:
        return value.split(arg)
    except:
        return [value] 

@register.filter
def slugify(value):
    """
    Convierte el valor a un 'slug' amigable para URL/ID.
    Necesario para generar IDs limpios para checkboxes de filtro.
    Ej: "Pago Mensual" -> "pago-mensual"
    """
    return django_slugify(value)

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Permite obtener un valor de un diccionario usando la clave.
    Útil si se necesita acceder a valores complejos en el template.
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

# --- FILTROS DE FORMATO ESPECÍFICO ---

@register.filter
def get_category_label(field_name):
    """
    Toma la clave numérica de la categoría (1, 2, 3...) y 
    devuelve la etiqueta legible asociada.
    Necesario para mostrar nombres legibles de categoría en la tabla.
    """
    if field_name is None:
        return ""
    try:
        # Asegura que field_name sea un entero para la búsqueda
        key = int(field_name) 
    except (ValueError, TypeError):
        return 'Concepto Desconocido'
    
    return CATEGORY_CHOICES_MAP.get(key, 'Concepto Desconocido')

# --- FILTROS DE MANEJO DE URL ---

@register.filter(name='remove_query_param')
def remove_query_param(url_querystring, param_name):
    """
    Elimina un parámetro específico de la query string (cadena de consulta).
    Esencial para mantener los filtros activos (ej: estado, q) al cambiar de página.
    Uso: request.GET.urlencode|remove_query_param:'page'
    """
    if not url_querystring:
        return ''
        
    query_dict = parse_qs(url_querystring, keep_blank_values=True)
    
    # Eliminar el parámetro solicitado
    if param_name in query_dict:
        del query_dict[param_name]
    
    # Reconstruir la query string
    new_querystring = urlencode(query_dict, doseq=True)
    
    # Devuelve la cadena con un '&' inicial si hay otros parámetros, sino una cadena vacía
    return '&' + new_querystring if new_querystring else ''

@register.filter
def moneda_ve(value):
    """
    Convierte un número al formato: 1.234.567,89
    """
    if value is None or value == "":
        return "0,00"
    
    try:
        # Formateamos con comas para miles y punto para decimales (estándar)
        value = "{:,.2f}".format(float(value))
        # Intercambiamos los signos usando una técnica de reemplazo temporal
        # 1,234,567.89 -> 1.234.567,89
        main_part, decimal_part = value.split('.')
        main_part = main_part.replace(',', '.')
        return f"{main_part},{decimal_part}"
    except (ValueError, TypeError):
        return value