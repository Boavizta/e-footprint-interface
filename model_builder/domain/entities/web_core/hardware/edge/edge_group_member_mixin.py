from model_builder.domain.services.group_membership_service import (
    apply_parent_group_memberships_from_form_data,
)


class EdgeGroupMemberMixin:
    """Shared behavior for objects that can belong to EdgeDeviceGroups (devices and sub-groups).

    Edit-panel membership sections come from the generic `dict_membership_sections` on
    `ModelingObjectWeb`; this mixin only keeps the creation-flow and deletion specifics.
    """

    # The pre_delete hook below removes self from parent group dicts, so the generic delete flow
    # must not treat those dicts as containers to edit (see DeleteObjectUseCase).
    handles_own_dict_memberships = True

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
