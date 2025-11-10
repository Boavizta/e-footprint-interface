from model_builder.web_core.usage.journey_step_base_web import JourneyStepBaseWeb


class UsageJourneyStepWeb(JourneyStepBaseWeb):
    @property
    def links_to(self):
        linked_server_ids = set([job.server.web_id for job in self.jobs])
        return "|".join(linked_server_ids)
