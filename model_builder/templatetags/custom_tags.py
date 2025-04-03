from django import template

register = template.Library()

@register.filter
def get_attr_from_template(obj, attr_name):
    return getattr(obj, attr_name)
