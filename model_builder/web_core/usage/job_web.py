from typing import TYPE_CHECKING

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.all_classes_in_order import SERVICE_CLASSES
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.usage.job import Job, GPUJob

from model_builder.class_structure import generate_object_creation_structure
from model_builder.form_references import FORM_TYPE_OBJECT
from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb, \
    ATTRIBUTES_TO_SKIP_IN_FORMS

if TYPE_CHECKING:
    from model_builder.web_core.usage.usage_journey_step_web import UsageJourneyStepWeb
    from model_builder.web_core.model_web import ModelWeb


class JobWeb(ModelingObjectWeb):
    @property
    def web_id(self):
        raise PermissionError(f"JobWeb objects don’t have a web_id attribute because their html "
                             f"representation should be managed by the MirroredJobWeb object")

    @property
    def mirrored_cards(self):
        mirrored_cards = []
        for usage_journey_step in self.usage_journey_steps:
            for mirrored_usage_journey_card in usage_journey_step.mirrored_cards:
                mirrored_cards.append(MirroredJobWeb(self._modeling_obj, mirrored_usage_journey_card))

        return mirrored_cards

    @classmethod
    def generate_object_creation_context(cls, model_web: "ModelWeb", efootprint_id_of_parent_to_link_to=None):
        servers = model_web.servers
        if len(servers) == 0:
            raise ValueError("Please go to the infrastructure section and create a server before adding a job")

        available_job_classes = {Job, GPUJob}
        for service in SERVICE_CLASSES:
            if service.__name__ in model_web.response_objs:
                available_job_classes.update(service.compatible_jobs())

        form_sections, dynamic_form_data = generate_object_creation_structure(
            "Job",
            available_efootprint_classes=list(available_job_classes),
            attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS,
            model_web=model_web,
        )
        additional_item = {
            "category": "job_creation_helper",
            "header": "Job creation helper",
            "fields": [
                {
                    "input_type": "select_object",
                    "web_id": "server",
                    "name": "Server",
                    "options": [
                        {"label": server.name, "value": server.efootprint_id} for server in servers],
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
        }
        form_sections = [additional_item] + form_sections

        possible_job_types_per_service = {
            "direct_server_call": [{"label": "Manually defined job", "value": "Job"}],
            "direct_server_call_gpu": [{"label": "Manually defined GPU job", "value": "GPUJob"}]
        }
        possible_job_types_per_service.update({
            service.efootprint_id: [
                {"label": FORM_TYPE_OBJECT[job.__name__]["label"], "value": job.__name__} for job in
                service.compatible_jobs()]
            for service in model_web.services}
        )
        dynamic_form_data["dynamic_selects"] = [
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
            }]

        context_data = {
            "form_sections": form_sections,
            "dynamic_form_data": dynamic_form_data,
            "object_type": "Job",
            "obj_formatting_data": FORM_TYPE_OBJECT["Job"],
            "header_name": "Add new " + FORM_TYPE_OBJECT["Job"]["label"].lower()
        }

        return context_data


class MirroredJobWeb(ModelingObjectWeb):
    def __init__(self, modeling_obj: ModelingObject, uj_step: "UsageJourneyStepWeb"):
        super().__init__(modeling_obj, uj_step.model_web)
        self.usage_journey_step = uj_step

    @property
    def settable_attributes(self):
        return super().settable_attributes + ["usage_journey_step"]

    @property
    def template_name(self):
        return "job"

    @property
    def web_id(self):
        return f"{self.class_as_simple_str}-{self.efootprint_id}_in_{self.usage_journey_step.web_id}"

    @property
    def links_to(self):
        return self.server.web_id

    @property
    def accordion_parent(self):
        return self.usage_journey_step

    @property
    def class_title_style(self):
        return "h8"
