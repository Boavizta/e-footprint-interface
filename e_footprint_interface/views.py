from utils import htmx_render


def home(request):
    return htmx_render(request, "home.html")
