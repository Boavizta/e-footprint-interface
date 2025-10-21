from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class StorageWeb(ModelingObjectWeb):
    attributes_to_skip_in_forms = ["fixed_nb_of_instances"]
