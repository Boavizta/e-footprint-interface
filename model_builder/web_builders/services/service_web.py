from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class ServiceWeb(ModelingObjectWeb):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gets_deleted_if_unique_mod_obj_container_gets_deleted = False

    @property
    def class_title_style(self):
        return "h8"

    @property
    def template_name(self):
        return "service"
