import json
import re

from django import template

register = template.Library()

@register.filter
def jsonify(value):
    return json.dumps(value)

@register.filter
def explain_format(value, mode="explainableQuantity"):
    if not isinstance(value, str):
        return value

    if mode == "explainableHourlyQuantities":
        value = value.split("first 10 vals")[0]
        value = value.replace("=", " =<br>")
    else:
        value = re.sub(r'=', '=<br>', value)
        value = value.replace('\n', '<br>')

    return value
