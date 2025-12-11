from typing import TYPE_CHECKING

from efootprint.all_classes_in_order import SERVICE_CLASSES
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.usage.job import Job, GPUJob

from model_builder.domain.entities.web_core.usage.resource_need_base_web import ResourceNeedBaseWeb

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb


class JobWeb(ResourceNeedBaseWeb):
    attributes_to_skip_in_forms = ["service", "server"]

    # Declarative form configuration - used by FormContextBuilder in adapters layer
    form_creation_config = {
        'strategy': 'parent_selection',
        'parent_attribute': 'server',
        'intermediate_attribute': 'service',
    }

    @property
    def links_to(self):
        return self.server.web_id

    @classmethod
    def get_creation_prerequisites(cls, model_web: "ModelWeb") -> dict:
        """Return raw domain data needed for form building.

        The adapter will transform this into form structures.
        No form field dictionaries here - just domain objects and relationships.
        """
        servers = model_web.servers
        if not servers:
            raise ValueError("Please go to the infrastructure section and create a server before adding a job")

        # Compute all available job classes based on services in system
        available_classes = {Job, GPUJob}
        for service_class in SERVICE_CLASSES:
            if service_class.__name__ in model_web.response_objs:
                available_classes.update(service_class.compatible_jobs())

        # Map: server → intermediate data (services + extra options for direct calls)
        intermediate_by_parent = {}
        for server in servers:
            is_gpu = isinstance(server.modeling_obj, GPUServer)
            intermediate_by_parent[server.efootprint_id] = {
                'items': server.installed_services,
                'extra_options': [{
                    'id': 'direct_server_call_gpu' if is_gpu else 'direct_server_call',
                    'label': f"direct call to{' GPU' if is_gpu else ''} server",
                    'type_classes': [GPUJob if is_gpu else Job],
                }],
            }

        # Map: service → list of compatible job classes
        type_classes_by_intermediate = {
            service.efootprint_id: list(service.compatible_jobs())
            for service in model_web.services
        }

        return {
            'parents': servers,
            'available_classes': list(available_classes),
            'intermediate_by_parent': intermediate_by_parent,
            'type_classes_by_intermediate': type_classes_by_intermediate,
        }
