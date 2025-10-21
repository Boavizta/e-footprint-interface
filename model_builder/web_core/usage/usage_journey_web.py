from model_builder.web_core.usage.journey_base_web import JourneyBaseWeb
from model_builder.web_core.usage.usage_journey_step_web import MirroredUsageJourneyStepWeb


class UsageJourneyWeb(JourneyBaseWeb):
    @property
    def child_object_type_str(self):
        return "UsageJourneyStep"

    @property
    def child_template_name(self):
        return "journey_step"

    @property
    def add_child_label(self):
        return "Add usage journey step"

    @property
    def children_property_name(self):
        return "uj_steps"

    @property
    def links_to(self):
        linked_server_ids = set()
        for uj_step in self.uj_steps:
            for job in uj_step.jobs:
                linked_server_ids.add(job.server.web_id)

        return "|".join(sorted(linked_server_ids))

    @property
    def accordion_children(self):
        return self.uj_steps

    @property
    def uj_steps(self):
        web_uj_steps = []
        for uj_step in self._modeling_obj.uj_steps:
            web_uj_steps.append(MirroredUsageJourneyStepWeb(uj_step, self))

        return web_uj_steps
