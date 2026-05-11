"""Builder for the ``{kind:target}`` placeholder handler dict.

``build_html_handlers`` returns handlers that emit HTML markup (anchors,
spans). Variable parts are escaped via Django's ``escape`` so the output is
safe to render with ``|safe``.

Handlers validate ``class:X``, ``param:X.y`` and ``calc:X.y`` targets against
``ALL_EFOOTPRINT_CLASSES_DICT``. Unknown ``ui`` tokens raise as well; ``doc``
slugs are not validated here (mkdocs build is authoritative).
"""
import inspect
from typing import Callable

from django.utils.html import escape
from efootprint.all_classes_in_order import ALL_EFOOTPRINT_CLASSES_DICT

from model_builder.adapters.ui_config import CLASS_UI_CONFIG, FIELD_UI_CONFIG


def _split_class_attr(target: str) -> tuple[str, str]:
    if "." not in target:
        raise ValueError(f"Expected 'Class.attr' target, got {target!r}")
    class_name, attr = target.split(".", 1)
    return class_name, attr


def _resolve_class(class_name: str) -> type:
    klass = ALL_EFOOTPRINT_CLASSES_DICT.get(class_name)
    if klass is None:
        raise ValueError(f"Unknown class in placeholder: {class_name!r}")
    return klass


def _class_label(class_name: str) -> str:
    return CLASS_UI_CONFIG.get(class_name, {}).get("label", class_name)


def _param_label(attr: str) -> str:
    return FIELD_UI_CONFIG.get(attr, {}).get("label", attr)


def _humanize(attr: str) -> str:
    return attr.replace("_", " ")


def _check_param(class_name: str, attr: str) -> None:
    klass = _resolve_class(class_name)
    init_params = inspect.signature(klass.__init__).parameters
    if attr not in init_params:
        raise ValueError(f"Unknown param {attr!r} for class {class_name!r}")


def _check_calc(class_name: str, attr: str) -> None:
    klass = _resolve_class(class_name)
    if attr not in klass.calculated_attributes:
        raise ValueError(f"Unknown calculated attribute {attr!r} for class {class_name!r}")


def build_html_handlers(ui_tokens: dict, mkdocs_base_url: str) -> dict[str, Callable[[str], str]]:
    def handle_class(target: str) -> str:
        _resolve_class(target)
        label = escape(_class_label(target))
        target_safe = escape(target)
        return (
            f'<a href="/model_builder/open-help-drawer/{target_safe}/" '
            f'class="help-drawer-trigger" '
            f'hx-get="/model_builder/open-help-drawer/{target_safe}/" '
            f'hx-target="#sidePanel">{label}</a>'
        )

    def handle_param(target: str) -> str:
        class_name, attr = _split_class_attr(target)
        _check_param(class_name, attr)
        label = escape(_param_label(attr))
        return f'<span class="ssot-param-ref">{label}</span>'

    def handle_calc(target: str) -> str:
        class_name, attr = _split_class_attr(target)
        _check_calc(class_name, attr)
        label = escape(_humanize(attr))
        return f'<span class="ssot-calc-ref">{label}</span>'

    def handle_doc(target: str) -> str:
        slug = escape(target)
        url = escape(f"{mkdocs_base_url.rstrip('/')}/{target}")
        return f'<a href="{url}" target="_blank" rel="noopener">{slug}</a>'

    def handle_ui(target: str) -> str:
        entry = ui_tokens.get(target)
        if entry is None:
            raise ValueError(f"Unknown UI token: {target!r}")
        display = escape(entry["display"])
        token_safe = escape(target)
        return f'<span class="ssot-ui-ref" data-ui-token="{token_safe}">{display}</span>'

    return {
        "class": handle_class,
        "param": handle_param,
        "calc": handle_calc,
        "doc": handle_doc,
        "ui": handle_ui,
    }
