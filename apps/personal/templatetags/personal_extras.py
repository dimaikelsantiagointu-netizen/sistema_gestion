from django import template

register = template.Library()

@register.filter(name='filter_by_name')
def filter_by_name(queryset, name):

    try:
        return queryset.filter(nombre_documento=name).first()
    except:
        return None