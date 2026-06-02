"""Domain services for e-footprint interface.

These services contain domain logic that doesn't depend on Django or HTTP concerns.
"""
from model_builder.domain.services.object_linking_service import ObjectLinkingService
from model_builder.domain.services.system_validation_service import SystemValidationService, ValidationResult, ValidationError
from model_builder.domain.services.emissions_calculation_service import EmissionsCalculationService, EmissionsResult
from model_builder.domain.services.edit_service import EditService, EditResult
from model_builder.domain.services.progressive_import_service import ProgressiveImportService
from model_builder.domain.services.empty_model import is_empty_model
from model_builder.domain.services.template_catalog_service import (
    CatalogEntry, CatalogGroup, OBSOLETE_HOW_TO_TEMPLATE_IDS, SCRATCH_ID,
    build_template_catalog, get_template_system_data,
)

__all__ = [
    "ObjectLinkingService",
    "SystemValidationService", "ValidationResult", "ValidationError",
    "EmissionsCalculationService", "EmissionsResult",
    "EditService", "EditResult",
    "ProgressiveImportService",
    "is_empty_model",
    "CatalogEntry", "CatalogGroup", "OBSOLETE_HOW_TO_TEMPLATE_IDS", "SCRATCH_ID",
    "build_template_catalog", "get_template_system_data",
]
