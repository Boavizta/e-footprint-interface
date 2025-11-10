from model_builder.web_core.usage.journey_base_web import JourneyBaseWeb


class UsageJourneyWeb(JourneyBaseWeb):
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
