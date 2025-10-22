from model_builder.web_core.usage.journey_step_base_web import JourneyStepBaseWeb, MirroredJourneyStepBaseWeb
from model_builder.web_core.usage.job_web import MirroredJobWeb


class UsageJourneyStepWeb(JourneyStepBaseWeb):
    @property
    def mirrored_cards(self):
        mirrored_cards = []
        for usage_journey in self.usage_journeys:
            mirrored_cards.append(MirroredUsageJourneyStepWeb(self._modeling_obj, usage_journey))

        return mirrored_cards


class MirroredUsageJourneyStepWeb(MirroredJourneyStepBaseWeb):
    @property
    def child_object_type_str(self):
        return "Job"

    @property
    def child_template_name(self):
        return "resource_need"

    @property
    def add_child_label(self):
        return "Add new job"

    @property
    def children_property_name(self):
        return "jobs"

    @property
    def links_to(self):
        linked_server_ids = set([job.server.web_id for job in self.jobs])
        return "|".join(linked_server_ids)

    @property
    def accordion_children(self):
        return self.jobs

    @property
    def jobs(self):
        web_jobs = []
        for job in self._modeling_obj.jobs:
            web_jobs.append(MirroredJobWeb(job, self))

        return web_jobs
