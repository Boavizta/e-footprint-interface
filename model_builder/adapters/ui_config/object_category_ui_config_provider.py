"""Object category UI configuration provider."""
from model_builder.adapters.ui_config import OBJECT_CATEGORY_UI_CONFIG


class ObjectCategoryUIConfigProvider:
    """Provides UI configuration for Sankey object categories."""

    @staticmethod
    def get_label(category_name: str) -> str:
        return OBJECT_CATEGORY_UI_CONFIG.get(category_name, {}).get("label", category_name)

    @staticmethod
    def get_category_names() -> list[str]:
        return sorted(OBJECT_CATEGORY_UI_CONFIG.keys(), key=len, reverse=True)
