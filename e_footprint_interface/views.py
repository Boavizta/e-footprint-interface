from utils import htmx_render


def home(request):
    return htmx_render(request, "home.html")


def server_error(request, *args, **kwargs):
    """Project-wide handler500 (production only): show the recovery page instead of a bare 500."""
    from model_builder.adapters.views.exception_handling import render_recovery_page
    return render_recovery_page(request, status=500)
