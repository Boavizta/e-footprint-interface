from model_builder.web_core.usage.journey_base_web import JourneyBaseWeb


class EdgeUsageJourneyWeb(JourneyBaseWeb):
    @property
    def links_to(self):
        linked_edge_device_ids = set()
        for edge_function in self.edge_functions:
            for recurrent_edge_resource_need in edge_function.recurrent_edge_device_needs:
                linked_edge_device_ids.add(recurrent_edge_resource_need.edge_device.web_id)

        return "|".join(sorted(linked_edge_device_ids))
