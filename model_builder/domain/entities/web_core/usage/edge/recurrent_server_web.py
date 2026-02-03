from efootprint.constants.sources import Sources

from model_builder.domain.entities.efootprint_extensions.explainable_recurrent_quantities_from_constant import \
    ExplainableRecurrentQuantitiesFromConstant
from model_builder.domain.entities.web_core.usage.resource_need_base_web import ResourceNeedBaseWeb


class RecurrentServerNeedWeb(ResourceNeedBaseWeb):
    default_values = {
        "recurrent_volume_per_edge_device": ExplainableRecurrentQuantitiesFromConstant(
            {"constant_value": 1, "constant_unit": "occurrence"}, source=Sources.HYPOTHESIS
        )
    }

    form_creation_config = {
        'strategy': 'simple',
    }

    @property
    def template_name(self):
        return "resource_need_with_accordion"

    @property
    def links_to(self):
        jobs_links = ""
        for job in self.jobs:
            job_links = job.links_to
            if jobs_links and job_links:
                jobs_links += "|" + job_links
            elif job_links:
                jobs_links += job_links
        if jobs_links:
            return self.edge_device.web_id + "|" + jobs_links
        return self.edge_device.web_id

    @classmethod
    def get_creation_prerequisites(cls, model_web: "ModelWeb") -> None:
        """Raise error if no edge devices exist in the model.
        """
        edge_devices = model_web.edge_devices
        if not edge_devices:
            raise ValueError("Please create an edge device before adding a recurrent server need")
