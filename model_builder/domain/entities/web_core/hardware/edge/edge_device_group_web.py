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

    @staticmethod
    def _count_to_display_value(count):
        magnitude = count.value.magnitude
        return int(magnitude) if float(magnitude).is_integer() else magnitude

    def _build_group_entry(self, obj, count):
        from model_builder.domain.efootprint_to_web_mapping import wrap_efootprint_object

        return {
            "object": wrap_efootprint_object(obj, self.model_web, self),
            "count": self._count_to_display_value(count),
        }

    @property
    def sub_group_entries(self):
        return [self._build_group_entry(group, count) for group, count in self.modeling_obj.sub_group_counts.items()]

    @property
    def edge_device_entries(self):
        return [self._build_group_entry(device, count) for device, count in self.modeling_obj.edge_device_counts.items()]

    @classmethod
    def pre_delete(cls, web_obj, model_web):
        """Remove group references from parent groups before deletion."""
        del model_web
        efp_obj = web_obj.modeling_obj
        for parent_dict in list(efp_obj.explainable_object_dicts_containers):
            if efp_obj in parent_dict:
                del parent_dict[efp_obj]
