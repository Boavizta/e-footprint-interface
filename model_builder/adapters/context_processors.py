"""Template context processors injected via TEMPLATES['OPTIONS']['context_processors']."""
from django.conf import settings


def edge_modeling_doc_url(request):
    del request
    return {
        "EDGE_MODELING_DOC_URL": getattr(settings, "EDGE_MODELING_DOC_URL", ""),
        "MKDOCS_BASE_URL": getattr(settings, "MKDOCS_BASE_URL", ""),
    }


def ai_bootstrap(request):
    """Expose only the availability of the server-configured bootstrap operation."""
    del request
    from model_builder.adapters.ai_provider import is_available
    return {"AI_BOOTSTRAP_AVAILABLE": is_available()}
