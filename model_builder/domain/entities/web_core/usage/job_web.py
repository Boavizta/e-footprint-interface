from typing import TYPE_CHECKING

from efootprint.all_classes_in_order import SERVICE_CLASSES, EXTERNAL_API_CLASSES, ALL_CONCRETE_EFOOTPRINT_CLASSES_DICT
from efootprint.builders.external_apis.external_api_job_base_class import ExternalAPIJob
from efootprint.builders.services.service_job_base_class import ServiceJob
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.usage.job import Job, GPUJob

from model_builder.domain.entities.web_core.usage.resource_need_base_web import ResourceNeedBaseWeb

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb


class JobWeb(ResourceNeedBaseWeb):
    attributes_to_skip_in_forms = ["service", "server", "external_api"]

    # Declarative form configuration - used by FormContextBuilder in adapters layer
    form_creation_config = {
        "strategy": "parent_selection",
        "parent_attribute": "server_or_external_api",
        "parent_attribute_label": "server or external API",
        "intermediate_attribute": "service_or_external_api",
        "intermediate_attribute_label": "Service or external API",
    }

    @property
    def links_to(self):
        if hasattr(self.modeling_obj, "external_api"):
            return self.external_api.web_id
        return self.server.web_id

    @classmethod
    def get_creation_prerequisites(cls, model_web: "ModelWeb") -> dict:
        """Return raw domain data needed for form building.

        The adapter will transform this into form structures.
        No form field dictionaries here - just domain objects and relationships.
        """
        servers = model_web.servers
        external_apis = model_web.external_apis
        if not servers + external_apis:
            raise ValueError(
                "Please go to the infrastructure section and create a server or external API before adding a job")

        # Compute all available job classes based on services and external APIs in system
        available_classes = {Job, GPUJob}
        for service_class in SERVICE_CLASSES + EXTERNAL_API_CLASSES:
            if service_class.__name__ in model_web.response_objs:
                available_classes.update(service_class.compatible_jobs())

        # Map: server → intermediate data (services + extra options for direct calls)
        intermediate_by_parent = {}
        for server in servers:
            is_gpu = isinstance(server.modeling_obj, GPUServer)
            intermediate_by_parent[server.efootprint_id] = {
                "items": server.installed_services,
                "extra_options": [{
                    "id": "direct_server_call_gpu" if is_gpu else "direct_server_call",
                    "label": f"direct call to{' GPU' if is_gpu else ''} server",
                    "type_classes": [GPUJob if is_gpu else Job],
                }],
            }

        # Map: service → list of compatible job classes
        type_classes_by_intermediate = {
            service.efootprint_id: list(service.compatible_jobs())
            for service in model_web.services
        }

        # External APIs will be considered both as servers and services.
        for external_api in external_apis:
            intermediate_by_parent[external_api.efootprint_id] = {"items": [external_api], "extra_options": []}
        type_classes_by_intermediate.update(
            {external_api.efootprint_id: list(external_api.compatible_jobs()) for external_api in external_apis})

        return {
            "parents": servers + external_apis,
            "available_classes": list(available_classes),
            "intermediate_by_parent": intermediate_by_parent,
            "type_classes_by_intermediate": type_classes_by_intermediate,
        }

    @classmethod
    def pre_create(cls, form_data, model_web: "ModelWeb"):
        """Adapt dependent object (server, service, external api) to job type.
        """
        if "service_or_external_api" not in form_data and "server_or_external_api" not in form_data:
            # Case of creating object forms directly from annotations in tests.
            return form_data

        efootprint_class_str = form_data.get("type_object_available")
        efootprint_class = ALL_CONCRETE_EFOOTPRINT_CLASSES_DICT[efootprint_class_str]
        if issubclass(efootprint_class, ExternalAPIJob):
            form_data["external_api"] = form_data["service_or_external_api"]
        elif issubclass(efootprint_class, ServiceJob):
            form_data["service"] = form_data["service_or_external_api"]
        else:
            form_data["server"] = form_data["server_or_external_api"]
        del form_data["service_or_external_api"]
        del form_data["server_or_external_api"]

        return form_data
