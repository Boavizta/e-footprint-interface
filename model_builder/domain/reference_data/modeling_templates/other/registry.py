"""Registry of ad-hoc "other" modeling templates owned by the interface.

Empty but wired: ad-hoc examples that fit neither the introductory set nor the
library how-to guides can be added here later with no new plumbing. They reuse
``IntroTemplate`` from the introductory registry.
"""
from model_builder.domain.reference_data.modeling_templates.introductory.registry import IntroTemplate

CATEGORY = "other"

OTHER_TEMPLATES: tuple[IntroTemplate, ...] = ()
