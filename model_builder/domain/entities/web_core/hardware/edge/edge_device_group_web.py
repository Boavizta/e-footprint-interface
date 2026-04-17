from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb
from model_builder.domain.entities.web_core.hardware.edge.edge_group_member_mixin import EdgeGroupMemberMixin
from model_builder.domain.services.group_membership_service import PARENT_GROUP_MEMBERSHIPS_FIELD


class EdgeDeviceGroupWeb(EdgeGroupMemberMixin, ModelingObjectWeb):
    add_template = "add_edge_device_group.html"
    edit_template = "edit_edge_device_group.html"
    gets_deleted_if_unique_mod_obj_container_gets_deleted = False
    form_creation_config = {"strategy": "simple"}

    @property
    def template_name(self):
        return "edge_device_group"

    @property
    def _parent_group_membership_dict(self) -> str:
        return "sub_group_counts"

    def _ancestor_ids(self) -> set:
        return {group.id for group in self.modeling_obj._find_all_ancestor_groups()}

    def get_edition_context_overrides(self) -> dict:
        context = super().get_edition_context_overrides()
        # A group cannot join itself or one of its descendants (cycle prevention).
        ancestor_ids = self._ancestor_ids()
        context["available_groups_to_join"] = [
            g for g in context["available_groups_to_join"]
            if g.efootprint_id != self.efootprint_id and g.efootprint_id not in ancestor_ids
        ]
        return context

    def filter_dict_count_options(self, attr_name, available_options):
        options = super().filter_dict_count_options(attr_name, available_options)
        if attr_name != "sub_group_counts":
            return options
        # Exclude ancestors: picking an ancestor as a sub-group would create a cycle.
        return [obj for obj in options if obj.efootprint_id not in self._ancestor_ids()]

    @classmethod
    def pre_create(cls, form_data, model_web):
        parent_ids = set((form_data.get(PARENT_GROUP_MEMBERSHIPS_FIELD) or {}).keys())
        sub_group_ids = set((form_data.get("sub_group_counts") or {}).keys())
        overlap = parent_ids & sub_group_ids
        if overlap:
            raise ValueError("A group cannot be both a parent and a subgroup of the same group.")
        return form_data

    def create_side_effects(self):
        from model_builder.domain.oob_region import OobRegion
        side_effects = super().create_side_effects()
        side_effects.oob_regions.append(OobRegion("edge_device_lists"))
        side_effects.replaces_primary_render = True
        return side_effects

    def edit_side_effects(self):
        from model_builder.domain.oob_region import OobRegion
        side_effects = super().edit_side_effects()
        side_effects.oob_regions.append(OobRegion("edge_device_lists"))
        side_effects.replaces_primary_render = True
        return side_effects

    def delete_side_effects(self):
        from model_builder.domain.oob_region import OobRegion
        regions = super().delete_side_effects()
        regions.append(OobRegion("edge_device_lists"))
        return regions

    def _build_group_entry(self, obj, count):
        from model_builder.domain.efootprint_to_web_mapping import wrap_efootprint_object

        return {
            "object": wrap_efootprint_object(obj, self.model_web, dict_container=self),
            "count": count.value.magnitude,
        }

    @property
    def sub_group_entries(self):
        return [self._build_group_entry(group, count) for group, count in self.modeling_obj.sub_group_counts.items()]

    @property
    def edge_device_entries(self):
        return [self._build_group_entry(device, count) for device, count in self.modeling_obj.edge_device_counts.items()]
