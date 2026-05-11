"""Adapter that resolves library + interface descriptive content into HTML.

The ``EFOOTPRINT_DESCRIPTION_PROVIDER`` module-level singleton is built at
import time with HTML-mode handlers. Every method returns a placeholder-resolved
``SafeString`` (or ``None``); callers render with ``|safe`` and templates never
see raw ``{kind:target}`` tokens.
"""
import inspect
from typing import Callable

from django.conf import settings
from django.utils.html import escape
from django.utils.safestring import SafeString, mark_safe
from efootprint.all_classes_in_order import ALL_EFOOTPRINT_CLASSES_DICT
from efootprint.utils.placeholder_resolver import resolve_placeholders

from model_builder.adapters.ui_config import CLASS_UI_CONFIG, FIELD_UI_CONFIG
from model_builder.adapters.ui_config.interface_placeholder_handlers import build_html_handlers
from model_builder.adapters.ui_config.ui_token_registry import UI_TOKENS


class EfootprintDescriptionProvider:
    def __init__(self, handlers: dict[str, Callable[[str], str]]):
        self._handlers = handlers
        self._class_cache: dict[str, type] = {}

    def class_description(self, class_name: str) -> SafeString | None:
        return self._resolve_attr(class_name, "__doc__")

    def class_disambiguation(self, class_name: str) -> SafeString | None:
        return self._resolve_attr(class_name, "disambiguation")

    def class_pitfalls(self, class_name: str) -> SafeString | None:
        return self._resolve_attr(class_name, "pitfalls")

    def class_interactions(self, class_name: str) -> SafeString | None:
        klass = self._resolve_class(class_name)
        for ancestor in klass.__mro__:
            text = CLASS_UI_CONFIG.get(ancestor.__name__, {}).get("interactions")
            if text:
                return self._resolve(text)
        return None

    def param_description(self, class_name: str, param: str) -> SafeString | None:
        klass = self._resolve_class(class_name)
        text = getattr(klass, "param_descriptions", {}).get(param)
        return self._resolve(text) if text else None

    def field_tooltip(self, class_name: str, param: str) -> SafeString | None:
        klass = self._resolve_class(class_name)
        library_text = getattr(klass, "param_descriptions", {}).get(param)
        interface_text = FIELD_UI_CONFIG.get(param, {}).get("tooltip")
        return self._merge(library_text, interface_text)

    def calc_description(self, class_name: str, attr: str) -> SafeString | None:
        klass = self._resolve_class(class_name)
        method = getattr(klass, f"update_{attr}", None)
        text = getattr(method, "__doc__", None) if method else None
        return self._resolve(text) if text else None

    def param_interaction(self, class_name: str, param: str) -> SafeString | None:
        klass = self._resolve_class(class_name)
        text = getattr(klass, "param_interactions", {}).get(param) if hasattr(klass, "param_interactions") else None
        return self._resolve(text) if text else None

    def _resolve_class(self, class_name: str) -> type:
        cached = self._class_cache.get(class_name)
        if cached is not None:
            return cached
        klass = ALL_EFOOTPRINT_CLASSES_DICT.get(class_name)
        if klass is None:
            raise ValueError(f"Unknown efootprint class: {class_name!r}")
        self._class_cache[class_name] = klass
        return klass

    def _resolve_attr(self, class_name: str, attr: str) -> SafeString | None:
        klass = self._resolve_class(class_name)
        text = getattr(klass, attr, None)
        if not text:
            return None
        return self._resolve(text)

    def _resolve(self, text: str) -> SafeString:
        return mark_safe(resolve_placeholders(text, self._handlers))

    def _merge(self, library_text: str | None, interface_text: str | None) -> SafeString | None:
        if not library_text and not interface_text:
            return None
        if library_text and not interface_text:
            return self._resolve(library_text)
        if interface_text and not library_text:
            # Legacy interface tooltips don't go through the resolver; escape them.
            return mark_safe(escape(interface_text))
        return mark_safe(
            f"{resolve_placeholders(library_text, self._handlers)}<br><br>{escape(interface_text)}"
        )


EFOOTPRINT_DESCRIPTION_PROVIDER = EfootprintDescriptionProvider(
    build_html_handlers(UI_TOKENS, settings.MKDOCS_BASE_URL)
)
