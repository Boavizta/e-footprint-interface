from typing import TYPE_CHECKING

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject

from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb
from model_builder.web_core.usage.job_web import MirroredJobWeb

if TYPE_CHECKING:
    from model_builder.web_core.usage.usage_journey_web import UsageJourneyWeb


class UsageJourneyStepWeb(ModelingObjectWeb):
    @property
    def web_id(self):
        raise PermissionError(f"UsageJourneyStepWeb objects don’t have a web_id attribute because their html "
                             f"representation should be managed by the MirroredUsageJourneyStepWeb object")

    @property
    def mirrored_cards(self):
        mirrored_cards = []
        for usage_journey in self.usage_journeys:
            mirrored_cards.append(MirroredUsageJourneyStepWeb(self._modeling_obj, usage_journey))

        return mirrored_cards


class MirroredUsageJourneyStepWeb(UsageJourneyStepWeb):
    def __init__(self, modeling_obj: ModelingObject, usage_journey: "UsageJourneyWeb"):
        super().__init__(modeling_obj, usage_journey.model_web)
        self.usage_journey = usage_journey

    @property
    def settable_attributes(self):
        return super().settable_attributes + ["usage_journey"]

    @property
    def web_id(self):
        return f"{self.class_as_simple_str}-{self.efootprint_id}_in_{self.usage_journey.web_id}"

    @property
    def links_to(self):
        linked_server_ids = set([job.server.web_id for job in self.jobs])
        return "|".join(linked_server_ids)

    @property
    def accordion_parent(self):
        return self.usage_journey

    @property
    def accordion_children(self):
        return self.jobs

    @property
    def jobs(self):
        web_jobs = []
        for job in self._modeling_obj.jobs:
            web_jobs.append(MirroredJobWeb(job, self))

        return web_jobs

    @property
    def icon_links_to(self):
        usage_journey_steps = self.usage_journey.uj_steps
        index = usage_journey_steps.index(self)
        if index < len(usage_journey_steps) - 1:
            link_to = f"icon-{usage_journey_steps[index+1].web_id}"
        else:
            link_to = f'add-usage-pattern-{self.usage_journey.web_id}'

        return link_to

    @property
    def icon_leaderline_style(self):
        usage_journey_steps = self.usage_journey.uj_steps
        index = usage_journey_steps.index(self)
        if index < len(usage_journey_steps) - 1:
            class_name = "vertical-step-swimlane"
        else:
            class_name = 'step-dot-line'

        return class_name

    @property
    def class_title_style(self):
        return "h7"

    @property
    def data_attributes_as_list_of_dict(self):
        data_attribute_updates = super().data_attributes_as_list_of_dict
        data_attribute_updates.append(
            {'id': f'icon-{self.web_id}', 'data-link-to': self.icon_links_to,
             'data-line-opt': self.icon_leaderline_style})

        return data_attribute_updates
