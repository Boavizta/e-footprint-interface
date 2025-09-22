from efootprint.all_classes_in_order import ALL_EFOOTPRINT_CLASSES
from efootprint.core.hardware.server_base import ServerBase
from efootprint.core.usage.job import JobBase

from model_builder.efootprint_extensions.edge_usage_pattern_from_form import EdgeUsagePatternFromForm
from model_builder.efootprint_extensions.recurrent_edge_process_from_form import RecurrentEdgeProcessFromForm
from model_builder.efootprint_extensions.usage_pattern_from_form import UsagePatternFromForm

_extension_classes = [UsagePatternFromForm, RecurrentEdgeProcessFromForm, EdgeUsagePatternFromForm]

MODELING_OBJECT_CLASSES_DICT = {modeling_object_class.__name__: modeling_object_class
                                for modeling_object_class in ALL_EFOOTPRINT_CLASSES + _extension_classes}
ABSTRACT_EFOOTPRINT_MODELING_CLASSES = {"JobBase": JobBase, "ServerBase": ServerBase}
