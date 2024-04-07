from django.contrib import admin
from django.urls import include, path
from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("understand", views.understand, name="understand"),
    path("quiz/", include("quiz.urls")),
    path("analyze/", include("analyze.urls")),
    path("admin/", admin.site.urls),
    path("__reload__/", include("django_browser_reload.urls")),
]
