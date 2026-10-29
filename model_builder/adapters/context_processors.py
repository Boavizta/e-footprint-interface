"""Template context processors injected via TEMPLATES['OPTIONS']['context_processors']."""
import os

from django.conf import settings


def edge_modeling_doc_url(request):
    del request
    return {
        "EDGE_MODELING_DOC_URL": getattr(settings, "EDGE_MODELING_DOC_URL", ""),
        "MKDOCS_BASE_URL": getattr(settings, "MKDOCS_BASE_URL", ""),
    }


AI_ASSISTANT_KEY_ENV = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "mistral": "MISTRAL_API_KEY"}


def ai_assistant(request):
    """Flag and selectable models of the experimental AI assistant; the sandbox is imported only when enabled."""
    del request
    if not settings.AI_ASSISTANT_ENABLED:
        return {"AI_ASSISTANT_ENABLED": False}
    from model_builder.adapters.views.views_ai_assistant import DEFAULT_MODELS, MODELS
    models = [(name, bool(os.environ.get(AI_ASSISTANT_KEY_ENV[MODELS[name][0]]))) for name in DEFAULT_MODELS]
    default_model = next((name for name, available in models if available), DEFAULT_MODELS[0])
    return {"AI_ASSISTANT_ENABLED": True, "AI_ASSISTANT_MODELS": models, "AI_ASSISTANT_DEFAULT_MODEL": default_model}
