"""Adapter that resolves library + interface descriptive content into HTML.

The ``EFOOTPRINT_DESCRIPTION_PROVIDER`` module-level singleton is built at
import time with HTML-mode handlers. Every method returns a placeholder-resolved
``SafeString`` (or ``None``); callers render with ``|safe`` and templates never
see raw ``{kind:target}`` tokens.

Interface-only abstract bases (``CLASS_UI_CONFIG`` keys that are not real
efootprint classes, e.g. ``EdgeDeviceBase``) are first-class: class-level
methods fall back to JSON-authored content when no Python class exists.
"""
import inspect
from typing import Callable

from django.conf import settings
from django.utils.safestring import SafeString, mark_safe
from efootprint.all_classes_in_order import ALL_CONCRETE_EFOOTPRINT_CLASSES_DICT, ALL_EFOOTPRINT_CLASSES_DICT
from efootprint.utils.placeholder_resolver import resolve_placeholders

from model_builder.adapters.ui_config import CLASS_UI_CONFIG, FIELD_UI_CONFIG
from model_builder.adapters.ui_config.interface_placeholder_handlers import build_html_handlers
from model_builder.adapters.ui_config.ui_token_registry import UI_TOKENS


class EfootprintDescriptionProvider:
    def __init__(self, handlers: dict[str, Callable[[str], str]]):
        self._handlers = handlers

    def class_description(self, class_name: str) -> SafeString | None:
        self._assert_known(class_name)
        # Interface-authored description wins when present; otherwise fall back
        # to the library docstring (dedented via ``inspect.getdoc``).
        text = CLASS_UI_CONFIG.get(class_name, {}).get("description")
        if text is None:
            klass = ALL_EFOOTPRINT_CLASSES_DICT.get(class_name)
            text = inspect.getdoc(klass) if klass else None
        return self._resolve(text) if text else None

    def class_disambiguation(self, class_name: str) -> SafeString | None:
        return self._resolve_class_attr(class_name, "disambiguation")

    def class_pitfalls(self, class_name: str) -> SafeString | None:
        return self._resolve_class_attr(class_name, "pitfalls")

    def class_interactions(self, class_name: str) -> SafeString | None:
        self._assert_known(class_name)
        klass = ALL_EFOOTPRINT_CLASSES_DICT.get(class_name)
        if klass is None:
            text = CLASS_UI_CONFIG.get(class_name, {}).get("interactions")
            return self._resolve(text) if text else None
        for ancestor in klass.__mro__:
            text = CLASS_UI_CONFIG.get(ancestor.__name__, {}).get("interactions")
            if text:
                return self._resolve(text)
        return None

    def class_doc_link(self, class_name: str) -> SafeString:
        self._assert_known(class_name)
        doc_classes = self._doc_classes(class_name)
        return mark_safe(", ".join(self._doc_link(doc_class) for doc_class in doc_classes))

    def param_description(self, class_name: str, param: str) -> SafeString | None:
        text = self._raw_param_description(class_name, param)
        return self._resolve(text) if text else None

    def field_tooltip(self, class_name: str, param: str) -> SafeString | None:
        library_text = self._raw_param_description(class_name, param)
        interface_text = FIELD_UI_CONFIG.get(param, {}).get("tooltip")
        return self._merge(library_text, interface_text)

    def interface_only_tooltip(self, param: str) -> SafeString | None:
        text = FIELD_UI_CONFIG.get(param, {}).get("tooltip")
        return self._resolve(text) if text else None

    def calc_description(self, class_name: str, attr: str) -> SafeString | None:
        klass = self._require_efootprint_class(class_name)
        method = getattr(klass, f"update_{attr}", None)
        text = inspect.getdoc(method) if method else None
        return self._resolve(text) if text else None

    def param_interaction(self, class_name: str, param: str) -> SafeString | None:
        klass = self._require_efootprint_class(class_name)
        text = getattr(klass, "param_interactions", {}).get(param)
        return self._resolve(text) if text else None

    def _assert_known(self, class_name: str) -> None:
        if class_name not in ALL_EFOOTPRINT_CLASSES_DICT and class_name not in CLASS_UI_CONFIG:
            raise ValueError(f"Unknown class: {class_name!r}")

    def _require_efootprint_class(self, class_name: str) -> type:
        klass = ALL_EFOOTPRINT_CLASSES_DICT.get(class_name)
        if klass is None:
            raise ValueError(f"Unknown efootprint class: {class_name!r}")
        return klass

    def _raw_param_description(self, class_name: str, param: str) -> str | None:
        klass = self._require_efootprint_class(class_name)
        return getattr(klass, "param_descriptions", {}).get(param)

    def _doc_classes(self, class_name: str) -> list[type]:
        if class_name in ALL_CONCRETE_EFOOTPRINT_CLASSES_DICT:
            return [ALL_CONCRETE_EFOOTPRINT_CLASSES_DICT[class_name]]

        available_classes = self._static_available_classes(class_name)
        if available_classes:
            return available_classes

        klass = self._require_efootprint_class(class_name)
        return [
            concrete_class
            for concrete_class in ALL_CONCRETE_EFOOTPRINT_CLASSES_DICT.values()
            if issubclass(concrete_class, klass)
        ]

    @staticmethod
    def _static_available_classes(class_name: str) -> list[type]:
        from model_builder.domain.efootprint_to_web_mapping import EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING

        web_class = EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING.get(class_name)
        config = getattr(web_class, "form_creation_config", {}) if web_class else {}
        return config.get("available_classes", [])

    def _doc_link(self, doc_class: type) -> str:
        class_name = doc_class.__name__
        label = CLASS_UI_CONFIG.get(class_name, {}).get("label", class_name)
        return self._handlers["doc"](f"{class_name}|{label}")

    def _resolve_class_attr(self, class_name: str, attr: str) -> SafeString | None:
        self._assert_known(class_name)
        klass = ALL_EFOOTPRINT_CLASSES_DICT.get(class_name)
        if klass is None:
            return None
        text = getattr(klass, attr, None)
        return self._resolve(text) if text else None

    def _resolve(self, text: str) -> SafeString:
        return mark_safe(resolve_placeholders(text, self._handlers))

    def _merge(self, library_text: str | None, interface_text: str | None) -> SafeString | None:
        if not library_text and not interface_text:
            return None
        if library_text and not interface_text:
            return self._resolve(library_text)
        if interface_text and not library_text:
            return self._resolve(interface_text)
        return mark_safe(f"{self._resolve(library_text)}<br><br>{self._resolve(interface_text)}")


EFOOTPRINT_DESCRIPTION_PROVIDER = EfootprintDescriptionProvider(
    build_html_handlers(UI_TOKENS, settings.MKDOCS_BASE_URL)
)
