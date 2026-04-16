from model_builder.domain.services.group_membership_service import (
    apply_parent_group_memberships_from_form_data,
)


def _build_group_membership_row(group, magnitude) -> dict:
    return {"group_id": group.id, "group_name": group.name, "count": magnitude}


class EdgeGroupMemberMixin:
    """Shared behavior for objects that can belong to EdgeDeviceGroups (devices and sub-groups)."""

    @property
    def _parent_group_membership_dict(self) -> str:
        """Name of the ExplainableObjectDict attribute on the parent group that holds self."""
        raise NotImplementedError

    def get_edition_context_overrides(self) -> dict:
        parent_groups = self.modeling_obj._find_parent_groups()
        parent_ids = {group.id for group in parent_groups}
        dict_attr = self._parent_group_membership_dict
        available_groups_to_join = sorted(
            [g for g in self.model_web.edge_device_groups if g.efootprint_id not in parent_ids],
            key=lambda g: g.name,
        )
        return {
            "group_memberships": [
                _build_group_membership_row(group, getattr(group, dict_attr)[self.modeling_obj].value.magnitude)
                for group in sorted(parent_groups, key=lambda g: g.name)
            ],
            "available_groups_to_join": available_groups_to_join,
        }

    @classmethod
    def get_creation_context_overrides(cls, model_web) -> dict:
        return {
            "available_groups_to_join": sorted(
                model_web.edge_device_groups, key=lambda g: g.name),
        }

    @classmethod
    def post_create(cls, added_obj, form_data, model_web):
        apply_parent_group_memberships_from_form_data(added_obj, form_data, model_web)
        return None

    @classmethod
    def pre_delete(cls, web_obj, model_web):
        """Remove references from parent groups before deletion."""
        del model_web
        efp_obj = web_obj.modeling_obj
        for parent_dict in list(efp_obj.explainable_object_dicts_containers):
            if efp_obj in parent_dict:
                del parent_dict[efp_obj]
