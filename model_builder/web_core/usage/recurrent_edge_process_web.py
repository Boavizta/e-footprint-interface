from typing import TYPE_CHECKING

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject

from model_builder.web_abstract_modeling_classes.modeling_object_that_can_be_mirrored import \
    ModelingObjectWebThatCanBeMirrored
from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb
from model_builder.web_core.usage.recurrent_edge_resource_need_web import RecurrentEdgeResourceNeedWeb

if TYPE_CHECKING:
    from model_builder.web_core.usage.edge_function_web import EdgeFunctionWeb


class RecurrentEdgeProcessWeb(RecurrentEdgeResourceNeedWeb, ModelingObjectWebThatCanBeMirrored):
    @property
    def mirrored_cards(self):
        mirrored_cards = []
        for edge_function in self.edge_functions:
            mirrored_cards.append(MirroredRecurrentEdgeProcessWeb(self._modeling_obj, edge_function))

        return mirrored_cards


class RecurrentEdgeProcessWebFromFormWeb(RecurrentEdgeProcessWeb):
    # This class exists because the default generate_object_creation_context method uses the class name
    pass


class MirroredRecurrentEdgeProcessWeb(ModelingObjectWeb):
    def __init__(self, modeling_obj: ModelingObject, edge_function: "EdgeFunctionWeb"):
        super().__init__(modeling_obj, edge_function.model_web)
        self.edge_function = edge_function

    @property
    def settable_attributes(self):
        return super().settable_attributes + ["edge_function"]

    @property
    def web_id(self):
        return f"{self.class_as_simple_str}-{self.efootprint_id}_in_{self.edge_function.web_id}"

    @property
    def accordion_parent(self):
        return self.edge_function

    @property
    def class_title_style(self):
        return "h8"
