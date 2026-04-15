from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb
from model_builder.domain.entities.web_core.hardware.edge.edge_device_base_web import _build_group_membership_row
from model_builder.domain.services.group_membership_service import (
    apply_parent_group_memberships_from_form_data,
)


class EdgeDeviceGroupWeb(ModelingObjectWeb):
    add_template = "add_edge_device_group.html"
    edit_template = "edit_edge_device_group.html"
    gets_deleted_if_unique_mod_obj_container_gets_deleted = False
    form_creation_config = {"strategy": "simple"}

    @property
    def template_name(self):
        return "edge_device_group"

    def filter_dict_count_options(self, attr_name, available_options):
        options = super().filter_dict_count_options(attr_name, available_options)
        if attr_name != "sub_group_counts":
            return options
        # Exclude ancestors: picking an ancestor as a sub-group would create a cycle.
        ancestor_ids = {group.id for group in self.modeling_obj._find_all_ancestor_groups()}
        return [obj for obj in options if obj.efootprint_id not in ancestor_ids]

    def get_edition_context_overrides(self) -> dict:
        parent_groups = self.modeling_obj._find_parent_groups()
        parent_ids = {group.id for group in parent_groups}
        # A group can join another group X only if X is not self and self is not an ancestor of X
        # (otherwise we'd create a cycle). Also exclude existing parents.
        available_groups_to_join = sorted(
            [
                group for group in self.model_web.edge_device_groups
                if group.efootprint_id != self.efootprint_id
                and group.efootprint_id not in parent_ids
                and self.modeling_obj not in group.modeling_obj._find_all_ancestor_groups()
            ],
            key=lambda group: group.name,
        )

        return {
            "group_memberships": [
                _build_group_membership_row(group, group.sub_group_counts[self.modeling_obj].value.magnitude)
                for group in sorted(parent_groups, key=lambda group: group.name)
            ],
            "available_groups_to_join": available_groups_to_join,
        }

    @classmethod
    def get_creation_context_overrides(cls, model_web) -> dict:
        # A new group has no descendants, so any existing group is a valid parent candidate.
        return {
            "available_groups_to_join": sorted(
                model_web.edge_device_groups, key=lambda group: group.name),
        }

    @classmethod
    def post_create(cls, added_obj, form_data, model_web):
        apply_parent_group_memberships_from_form_data(added_obj, form_data, model_web)
        return None

    @classmethod
    def create_side_effects(cls, added_obj, model_web):
        from model_builder.domain.oob_region import CreateSideEffects, OobRegion
        del added_obj, model_web
        return CreateSideEffects(
            oob_regions=[OobRegion("edge_device_lists")], replaces_primary_render=True)

    def edit_side_effects(self):
        from model_builder.domain.oob_region import OobRegion
        return [OobRegion("edge_device_lists")]

    @classmethod
    def delete_side_effects(cls, web_obj, model_web):
        from model_builder.domain.oob_region import OobRegion
        del web_obj, model_web
        return [OobRegion("edge_device_lists")]

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

    @classmethod
    def pre_delete(cls, web_obj, model_web):
        """Remove group references from parent groups before deletion."""
        del model_web
        efp_obj = web_obj.modeling_obj
        for parent_dict in list(efp_obj.explainable_object_dicts_containers):
            if efp_obj in parent_dict:
                del parent_dict[efp_obj]
