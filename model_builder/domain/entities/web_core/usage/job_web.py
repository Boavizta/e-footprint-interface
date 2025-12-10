from typing import TYPE_CHECKING

from efootprint.all_classes_in_order import SERVICE_CLASSES
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.usage.job import Job, GPUJob

from model_builder.form_references import FORM_TYPE_OBJECT
from model_builder.domain.entities.web_core.usage.resource_need_base_web import ResourceNeedBaseWeb

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb


class JobWeb(ResourceNeedBaseWeb):
    attributes_to_skip_in_forms = ["service", "server"]

    # Declarative form configuration - used by FormContextBuilder in adapters layer
    form_creation_config = {
        'strategy': 'parent_selection',
        'object_type': 'Job',
    }

    @property
    def links_to(self):
        return self.server.web_id

    @classmethod
    def get_form_creation_data(cls, model_web: "ModelWeb") -> dict:
        """Provide form data for parent_selection strategy.

        Returns data for FormContextBuilder to build the form structure.
        Domain logic stays here; form generation happens in adapter.
        """
        servers = model_web.servers
        if len(servers) == 0:
            raise ValueError("Please go to the infrastructure section and create a server before adding a job")

        # Compute available job classes based on services in system
        available_job_classes = {Job, GPUJob}
        for service in SERVICE_CLASSES:
            if service.__name__ in model_web.response_objs:
                available_job_classes.update(service.compatible_jobs())

        # Build helper fields for server/service selection
        helper_fields = [
            {
                "input_type": "select_object",
                "web_id": "server",
                "name": "Server",
                "options": [{"label": server.name, "value": server.efootprint_id} for server in servers],
                "label": "Choose a server",
            },
            {
                "input_type": "select_object",
                "web_id": "service",
                "name": "Service used",
                "options": None,
                "label": "Service used",
            },
        ]

        # Build dynamic selects for cascading service → job type selection
        possible_job_types_per_service = {
            "direct_server_call": [{"label": "Manually defined job", "value": "Job"}],
            "direct_server_call_gpu": [{"label": "Manually defined GPU job", "value": "GPUJob"}]
        }
        possible_job_types_per_service.update({
            service.efootprint_id: [
                {"label": FORM_TYPE_OBJECT[job.__name__]["label"], "value": job.__name__}
                for job in service.compatible_jobs()]
            for service in model_web.services}
        )

        dynamic_selects = [
            {
                "input_id": "service",
                "filter_by": "server",
                "list_value": {
                    server.efootprint_id:
                        [{"label": service.name, "value": service.efootprint_id}
                         for service in server.installed_services]
                        + [{
                            "label": f"direct call to{' GPU' if isinstance(server.modeling_obj, GPUServer) else ''} server",
                            "value": f"direct_server_call{'_gpu' if isinstance(server.modeling_obj, GPUServer) else ''}"}]
                    for server in servers
                }
            },
            {
                "input_id": "type_object_available",
                "filter_by": "service",
                "list_value": possible_job_types_per_service
            }
        ]

        return {
            'available_classes': list(available_job_classes),
            'helper_fields': helper_fields,
            'dynamic_selects': dynamic_selects,
        }
