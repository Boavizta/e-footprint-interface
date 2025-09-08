from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb
from model_builder.web_core.usage.recurrent_edge_process_web import MirroredRecurrentEdgeProcessFromFormWeb


class EdgeUsageJourneyWeb(ModelingObjectWeb):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gets_deleted_if_unique_mod_obj_container_gets_deleted = False

    @property
    def links_to(self):
        return self.edge_device.web_id

    @property
    def accordion_children(self):
        return self.edge_processes

    @property
    def edge_processes(self):
        web_edge_processes = []
        for edge_process in self._modeling_obj.edge_processes:
            web_edge_processes.append(MirroredRecurrentEdgeProcessFromFormWeb(edge_process, self))

        return web_edge_processes

    @property
    def class_title_style(self):
        return "h6"
