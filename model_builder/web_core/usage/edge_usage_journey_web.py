from model_builder.web_core.usage.journey_base_web import JourneyBaseWeb


class EdgeUsageJourneyWeb(JourneyBaseWeb):
    @property
    def child_object_type_str(self):
        return "EdgeFunction"

    @property
    def child_template_name(self):
        return "journey_step"

    @property
    def add_child_label(self):
        return "Add edge function"

    @property
    def children_property_name(self):
        return "edge_functions"

    @property
    def links_to(self):
        linked_edge_device_ids = set()
        for edge_function in self.edge_functions:
            for recurrent_edge_resource_need in edge_function.recurrent_edge_device_needs:
                linked_edge_device_ids.add(recurrent_edge_resource_need.edge_device.web_id)

        return "|".join(sorted(linked_edge_device_ids))

    @property
    def accordion_children(self):
        return self.edge_functions

    @property
    def edge_functions(self):
        """Returns mirrored edge functions for display in this usage journey context."""
        from model_builder.web_core.usage.edge_function_web import MirroredEdgeFunctionWeb
        web_edge_functions = []
        for edge_function in self._modeling_obj.edge_functions:
            web_edge_functions.append(MirroredEdgeFunctionWeb(edge_function, self))

        return web_edge_functions
