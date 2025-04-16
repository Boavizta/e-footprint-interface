from django.contrib import admin
from django.urls import include, path
from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("model_builder/", include("model_builder.urls")),
    path("admin/", admin.site.urls),
    path("__reload__/", include("django_browser_reload.urls")),
]
