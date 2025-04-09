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
