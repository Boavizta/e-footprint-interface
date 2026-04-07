from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class EdgeDeviceGroupWeb(ModelingObjectWeb):
    add_template = "add_edge_device_group.html"
    attributes_to_skip_in_forms = ["sub_group_counts", "edge_device_counts"]
    gets_deleted_if_unique_mod_obj_container_gets_deleted = False

    @property
    def template_name(self):
        return "edge_device_group"

    @classmethod
    def prepare_creation_input(cls, form_data):
        form_data = dict(form_data)
        form_data["sub_group_counts"] = {}
        form_data["edge_device_counts"] = {}
        return form_data

    @classmethod
    def pre_delete(cls, web_obj, model_web):
        """Remove group references from parent groups before deletion."""
        del model_web
        efp_obj = web_obj.modeling_obj
        for parent_dict in list(efp_obj.explainable_object_dicts_containers):
            if efp_obj in parent_dict:
                del parent_dict[efp_obj]
