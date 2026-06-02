from django.contrib import admin
from django.urls import include, path
from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("model_builder/", include("model_builder.urls")),
    path("admin/", admin.site.urls),
    path("__reload__/", include("django_browser_reload.urls")),
]

# Project-wide safety net for unhandled 500s (only fires when DEBUG=False, i.e. in production):
# render the same recovery page so users can reset and report the bug instead of a blank error.
handler500 = "e_footprint_interface.views.server_error"
