from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class EdgeDeviceBaseWeb(ModelingObjectWeb):
    """Base web wrapper for EdgeDeviceBase and its subclasses (EdgeComputer, EdgeAppliance)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gets_deleted_if_unique_mod_obj_container_gets_deleted = False

    @property
    def class_title_style(self):
        return "h6"
