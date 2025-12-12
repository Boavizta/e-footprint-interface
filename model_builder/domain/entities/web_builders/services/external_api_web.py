import math
from typing import TYPE_CHECKING

from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.services.generative_ai_ecologits import GenAIModel
from efootprint.constants.units import u
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.hardware.server_base import ServerTypes
from efootprint.core.hardware.storage import Storage

from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb


class ExternalApiWeb(ModelingObjectWeb):
    # Store server reference for use after creation (needed for custom output)
    _created_server_web = None

    # Declarative form configuration - used by FormContextBuilder in adapters layer
    form_creation_config = {
        'strategy': 'simple',
        'form_object_type': 'Service',  # Use Service form structure
        'available_classes': [GenAIModel],
    }

    @classmethod
    def get_htmx_form_config(cls, context_data: dict) -> dict:
        """HTMX configuration for external API creation forms - append to #server-list."""
        return {"hx_target": "#server-list", "hx_swap": "beforeend"}

    @classmethod
    def pre_create(cls, form_data, model_web: "ModelWeb"):
        """Create storage and GPU server before creating the GenAI service."""
        service_type = form_data.get("type_object_available")
        if service_type != "GenAIModel":
            raise Exception(f"External service {service_type} not supported yet.")

        # Create storage
        new_storage = Storage.ssd()
        model_web.add_new_efootprint_object_to_system(new_storage)

        # Create GPU server
        service_name = form_data.get("name")
        new_server = GPUServer.from_defaults(
            name=f'{service_name} API servers', server_type=ServerTypes.serverless(),
            storage=new_storage, compute=SourceValue(1 * u.gpu))
        cls._created_server_web = model_web.add_new_efootprint_object_to_system(new_server)

        # Modify form data to reference the server (copy to avoid mutation)
        form_data = dict(form_data)
        form_data["efootprint_id_of_parent_to_link_to"] = new_server.id

        return form_data

    @classmethod
    def post_create(cls, created_service, form_data, model_web: "ModelWeb"):
        """Return server info instead of service."""
        return {
            "return_server_instead": True,
            "server_web": cls._created_server_web
        }

    @classmethod
    def handle_creation_error(cls, error, form_data, model_web: "ModelWeb"):
        """Handle InsufficientCapacityError by adjusting GPU count."""
        if isinstance(error, InsufficientCapacityError):
            server = cls._created_server_web.modeling_obj if cls._created_server_web else None
            if server and hasattr(server, 'installed_services') and server.installed_services:
                new_service = server.installed_services[0]
                nb_of_gpus_required = math.ceil((error.requested_capacity / server.ram_per_gpu).to(u.gpu).magnitude)
                server.compute = SourceValue(
                    nb_of_gpus_required * u.gpu, source=Source("Computed to match model size", link=None))
                # Re-run after_init because it had been interrupted by the error
                new_service.after_init()
                model_web.add_new_efootprint_object_to_system(new_service)
                return new_service
        raise error
