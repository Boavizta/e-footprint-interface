"""Template context processors injected via TEMPLATES['OPTIONS']['context_processors']."""
from django.conf import settings


def edge_modeling_doc_url(request):
    del request
    return {"EDGE_MODELING_DOC_URL": getattr(settings, "EDGE_MODELING_DOC_URL", "")}
