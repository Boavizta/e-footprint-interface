import os

from django.apps import AppConfig


class ModelBuilderConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "model_builder"

    def ready(self):
        if os.getenv('DJANGO_PROD') == 'True':
            from model_builder.model_web import MODELING_OBJECT_CLASSES_DICT
