import re
import unicodedata

from efootprint.constants.countries import Countries
from django.shortcuts import render


def camelcase_html_filename_from_path(html_file_path: str):
    html_filename = html_file_path.split("/")[-1].replace(".html", "")
    if "-" in html_filename:
        raise ValueError(f"HTML file name should not contain '-', please rename {html_filename} to "
                         f"{html_filename.replace('-', '_')}")
    if "_" in html_filename:
        parts = html_filename.split("_")
        html_filename = parts[0]
        for elt in parts[1:]:
            html_filename += elt.capitalize()

    return html_filename

def format_snakecase_string(string: str) -> str:
    format_str = str.replace(string, "_", " ")
    return format_str.capitalize()

def camel_to_snake(name: str) -> str:
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def smart_truncate(text, max_length=45, suffix='_[...]'):
    if len(text) <= max_length:
        return text
    cut_pos = max(text.rfind(sep, 0, max_length) for sep in [' ', '_', '-'])
    if cut_pos == -1 or cut_pos < 10:
        cut_pos = max_length
    return text[:cut_pos].rstrip() + suffix

def sanitize_filename(name):
    name = unicodedata.normalize('NFKD', name)
    name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
    return name


def htmx_render(request, html_file_path: str, context=None):
    if context is None:
        context = {}

    if request.headers.get("HX-Request") == "true":
        return render(request, html_file_path, context)
    else:
        html_filename = camelcase_html_filename_from_path(html_file_path)
        context[html_filename] = True
        response = render(request, "base.html", context)

        return response


EFOOTPRINT_COUNTRIES = []
for attr_value in vars(Countries).values():
    if callable(attr_value):
        EFOOTPRINT_COUNTRIES.append(attr_value())
