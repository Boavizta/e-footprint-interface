from efootprint.all_classes_in_order import ALL_EFOOTPRINT_CLASSES, CANONICAL_COMPUTATION_ORDER

# No extension classes needed anymore - timeseries generation is handled by ExplainableObject subclasses
_extension_classes = []

MODELING_OBJECT_CLASSES_DICT = {modeling_object_class.__name__: modeling_object_class
                                for modeling_object_class in ALL_EFOOTPRINT_CLASSES + _extension_classes}
ABSTRACT_EFOOTPRINT_MODELING_CLASSES = {modeling_object_class.__name__: modeling_object_class
                                        for modeling_object_class in CANONICAL_COMPUTATION_ORDER
                                        if modeling_object_class.__name__ not in MODELING_OBJECT_CLASSES_DICT}
