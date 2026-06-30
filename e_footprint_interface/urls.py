from django.contrib import admin
from django.urls import include, path
from . import views
from model_builder.adapters.views.views_onboarding import load_template_deeplink


urlpatterns = [
    path("", views.home, name="home"),
    # Live, intentionally-unlinked design catalogue for contributors (tokens + real components).
    path("design/", views.design_catalogue, name="design-catalogue"),
    # Shareable deep link from the docs' "Load this scenario" links → load it and land on the canvas.
    path("template/<str:template_id>/", load_template_deeplink, name="load-template-deeplink"),
    path("model_builder/", include("model_builder.urls")),
    path("admin/", admin.site.urls),
    path("__reload__/", include("django_browser_reload.urls")),
]

# Project-wide safety net for unhandled 500s (only fires when DEBUG=False, i.e. in production):
# render the same recovery page so users can reset and report the bug instead of a blank error.
handler500 = "e_footprint_interface.views.server_error"
