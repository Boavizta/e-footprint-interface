import re
from typing import TYPE_CHECKING, get_args, get_origin, Dict, List, Tuple, Optional

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject, get_instance_attributes
from efootprint.logger import logger
from efootprint.utils.tools import get_init_signature_params

from model_builder.domain.entities.web_abstract_modeling_classes.explainable_objects_web import (
    ExplainableQuantityWeb, ExplainableObjectWeb, ExplainableObjectDictWeb)
from model_builder.domain.entities.web_abstract_modeling_classes.object_linked_to_modeling_obj_web import ObjectLinkedToModelingObjWeb

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb


class ModelingObjectWeb:
    default_values = {}
    add_template = "add_panel__generic.html"
    edit_template = "edit_panel__generic.html"
    attributes_to_skip_in_forms = []
    # Maps the first segment of a cross-object conditional_list_values `depends_on` path
    # (e.g. "external_api" in "external_api.model_name") to the DOM id of the field that
    # actually carries that referenced object's selection, when it isn't rendered as
    # `{class}_{segment}` (e.g. because it's skipped in forms and chosen via a helper field).
    conditional_list_filter_overrides = {}
    gets_deleted_if_unique_mod_obj_container_gets_deleted = True

    def __init__(self, modeling_obj: ModelingObject, model_web: "ModelWeb", list_container=None, dict_container=None):
        self._modeling_obj = modeling_obj
        self.model_web = model_web
        self.list_container = list_container
        self.dict_container = dict_container

    @property
    def settable_attributes(self):
        return ["_modeling_obj", "model_web", "list_container", "dict_container"]

    def __getattr__(self, name):
        from model_builder.domain.efootprint_to_web_mapping import wrap_efootprint_object

        # Check if the attribute is defined in the class hierarchy (as a property, method, etc.)
        # If it is, we need to manually call it and let any error propagate
        for cls in type(self).__mro__:
            if name in cls.__dict__:
                attr_descriptor = cls.__dict__[name]
                # If it's a property, call its getter
                if isinstance(attr_descriptor, property):
                    return attr_descriptor.fget(self)
                # If it's another descriptor (like a method), get it normally
                elif hasattr(attr_descriptor, '__get__'):
                    return attr_descriptor.__get__(self, type(self))
                # Otherwise just return it
                else:
                    return attr_descriptor

        attr = getattr(self._modeling_obj, name)

        if name == "id":
            raise AttributeError("The id attribute shouldn’t be retrieved by ModelingObjectWrapper objects. "
                             "Use efootprint_id and web_id for clear disambiguation.")

        if isinstance(attr, list) and len(attr) > 0 and isinstance(attr[0], ModelingObject):
            list_container = self if name in self.list_attr_names else None
            return [wrap_efootprint_object(item, self.model_web, list_container=list_container) for item in attr]

        if isinstance(attr, ModelingObject):
            return wrap_efootprint_object(attr, self.model_web)

        if isinstance(attr, ExplainableQuantity):
            return ExplainableQuantityWeb(attr, self.model_web)

        if isinstance(attr, ExplainableObject):
            return ExplainableObjectWeb(attr, self.model_web)

        if isinstance(attr, ExplainableObjectDict):
            return ExplainableObjectDictWeb(attr, self.model_web)

        return attr

    def __setattr__(self, key, value):
        if key in self.settable_attributes:
            super.__setattr__(self, key, value)
        else:
            raise PermissionError(f"{self} is trying to set the {key} attribute with value {value}.")

    def __hash__(self):
        return hash(self.web_id)

    def __eq__(self, other):
        return self.web_id == other.web_id

    def set_efootprint_value(self, key, value, check_input_validity=True):
        error_message = (f"{self} tried to set a ModelingObjectWrapper attribute to its underlying e-footprint "
                         f"object, which is forbidden. Only set e-footprint objects as attributes of e-footprint "
                         f"objects.")
        if isinstance(value, list) and len(value) > 0 and isinstance(value[0], ModelingObjectWeb):
            raise PermissionError(error_message)

        if isinstance(value, ModelingObjectWeb):
            raise PermissionError(error_message)

        if isinstance(value, ObjectLinkedToModelingObjWeb):
            raise PermissionError(error_message)

        self._modeling_obj.__setattr__(key, value, check_input_validity)

    def get_efootprint_value(self, key):
        return getattr(self._modeling_obj, key, None)

    @property
    def calculated_attributes_values(self):
        return [self.__getattr__(attr_name) for attr_name in self.calculated_attributes_without_validations]

    def filter_dict_count_options(self, attr_name: str, available_options: list) -> list:
        """Filter options offered for an `ExplainableObjectDict[X]` attribute in the edit form.

        Default: exclude the object being edited so it cannot reference itself. Subclasses may
        override to apply domain-specific cycle filters (e.g. excluding ancestor groups).
        """
        del attr_name
        return [obj for obj in available_options if obj.efootprint_id != self.efootprint_id]

    @property
    def modeling_obj(self):
        return self._modeling_obj

    @property
    def modeling_paradigm(self) -> str:
        from model_builder.domain.modeling_paradigm import paradigm_for
        return paradigm_for(self._modeling_obj.class_as_simple_str)

    @property
    def efootprint_id(self):
        return self._modeling_obj.id

    @property
    def web_id(self):
        # Prefix the root card id with the system id so the two resident comparison canvases never
        # collide. Every derived id (`button-`/`flush-`/`icon-`), HTMX/
        # hyperscript selector, leaderline anchor and mirrored-card ref flows from web_id, so this one
        # chokepoint namespaces them all; the canvas templates need no edits. The nested branch
        # inherits the prefix through parent_container.web_id, so it is applied exactly once at the
        # root. The distinct-system-id workspace invariant keeps the two slots' prefixes distinct.
        if self.parent_container is not None:
            return f"{self.class_as_simple_str}-{self._modeling_obj.id}_in_{self.parent_container.web_id}"
        return f"{self._system_web_id_prefix}{self.class_as_simple_str}-{self._modeling_obj.id}"

    @property
    def _system_web_id_prefix(self) -> str:
        """``sys-{system id}-`` — the namespace that disambiguates the two resident canvases.

        The literal ``sys-`` is load-bearing: system ids are uuids that often start with a digit, and a
        bare ``{system id}-…`` prefix would make the web_id an invalid CSS id selector — HTMX resolves
        its OOB targets with ``querySelector('#'+id)``, which throws on a leading digit (object cards
        used to start with the class name, always a letter). A constant letter-leading prefix keeps
        every derived id a valid selector.
        """
        return f"sys-{self.model_web.system.efootprint_id}-"

    @property
    def value(self):
        return self.efootprint_id

    @property
    def label(self):
        return self.name

    @property
    def template_name(self):
        snake_case_class_name = re.sub(r'(?<!^)(?=[A-Z])', '_', self.class_as_simple_str).lower()
        return f"{snake_case_class_name}"

    @classmethod
    def get_htmx_form_config(cls, context_data: dict) -> dict:
        """
        Returns HTMX configuration for the object creation form.
        Override in subclasses to customize behavior for specific object types.

        Args:
            context_data: The context data dictionary passed to the template

        Returns:
            Dictionary with optional keys:
            - hx_vals: dict of additional values to pass via hx-vals
            - hx_target: CSS selector for target element
            - hx_swap: HTMX swap strategy
        """
        return {}  # Default: no special HTMX configuration

    @property
    def count_in_dict_container(self) -> Optional[float]:
        """This entry's weight in the dict container it is rendered under; None for list children."""
        if self.dict_container is None:
            return None
        from model_builder.domain.services.object_linking_service import resolve_dict_attr

        attr_name = resolve_dict_attr(self.dict_container.modeling_obj, self._modeling_obj)
        return getattr(self.dict_container.modeling_obj, attr_name)[self._modeling_obj].value.magnitude

    @property
    def dict_membership_sections(self) -> List[dict]:
        """Reverse view of `ExplainableObjectDict` relationships, for child-panel membership sections.

        One section per (parent class, dict attr) pair whose child annotation matches this object's
        class, listing current memberships (with their counts) and the parents it could still join.
        """
        from model_builder.domain.services.object_linking_service import dict_membership_specs

        sections = []
        for parent_class, attr_name in dict_membership_specs(type(self._modeling_obj)):
            parents = sorted(
                (obj for obj in self.model_web.flat_efootprint_objs_dict.values() if isinstance(obj, parent_class)),
                key=lambda parent: parent.name)
            memberships = [
                {"parent_id": parent.id, "parent_name": parent.name,
                 "count": getattr(parent, attr_name)[self._modeling_obj].value.magnitude}
                for parent in parents if self._modeling_obj in getattr(parent, attr_name)]
            member_ids = {membership["parent_id"] for membership in memberships}
            available_parents = self.filter_available_membership_parents(
                attr_name, [parent for parent in parents if parent.id not in member_ids])
            if memberships or available_parents:
                sections.append({
                    "parent_class_name": parent_class.__name__, "attr_name": attr_name,
                    "memberships": memberships,
                    "available_parents": [
                        {"efootprint_id": parent.id, "name": parent.name} for parent in available_parents]})
        return sections

    def filter_available_membership_parents(self, attr_name: str, candidate_parents: list) -> list:
        """Filter the parents offered in a membership section's "Add to…" select.

        Default: exclude the object itself (no self-containment). Subclasses may override to apply
        domain-specific cycle filters (e.g. excluding descendant groups).
        """
        del attr_name
        return [parent for parent in candidate_parents if parent.id != self.efootprint_id]

    def _recompute_state_and_emit_oob_regions(self) -> list:
        """Diff post-mutation state vs. last-emitted state; return OOB regions for each flip.

        Two diffs share this hook:
          * `model_web.creation_constraints` flips emit `model_canvas` + `results_buttons`
            regions and stage `model_web.constraint_changes` for the presenter's toasts.
          * `model_web.has_edge_objects` flips emit the `edge_modeling_toggle` region
            so the navbar toggle re-renders latched/unlatched.

        Called from all three `*_side_effects` hooks so the diff-and-emit logic lives in
        exactly one place.
        """
        from model_builder.domain.oob_region import OobRegion

        model_web = self.model_web
        new_constraints = model_web._build_creation_constraints()
        old_constraints = model_web.creation_constraints
        changes = []
        for key, value in new_constraints.items():
            if key not in old_constraints:
                continue
            if old_constraints[key]["enabled"] != value["enabled"]:
                changes.append((key, "unlocked" if value["enabled"] else "locked"))
        results_reason_changed = (
            "__results__" in old_constraints
            and old_constraints["__results__"].get("reason")
                != new_constraints["__results__"].get("reason")
        )
        model_web.creation_constraints = new_constraints

        regions: list = []
        if changes:
            model_web.constraint_changes = changes
            regions.extend([OobRegion("model_canvas"), OobRegion("results_buttons")])
        elif results_reason_changed:
            regions.append(OobRegion("results_buttons"))

        new_has_edge = model_web.has_edge_objects
        if new_has_edge != model_web._last_emitted_has_edge_objects:
            model_web._last_emitted_has_edge_objects = new_has_edge
            regions.append(OobRegion("edge_modeling_toggle"))

        return regions

    def create_side_effects(self):
        """Side-effect descriptors emitted after this object is created."""
        from model_builder.domain.oob_region import CreateSideEffects
        side_effects = CreateSideEffects()
        side_effects.oob_regions.extend(self._recompute_state_and_emit_oob_regions())
        return side_effects

    def edit_side_effects(self):
        """Side-effect descriptors emitted after this object is edited."""
        from model_builder.domain.oob_region import EditSideEffects
        side_effects = EditSideEffects()
        side_effects.oob_regions.extend(self._recompute_state_and_emit_oob_regions())
        return side_effects

    def delete_side_effects(self):
        """Side-effect OOB regions emitted after this object is deleted."""
        return self._recompute_state_and_emit_oob_regions()


    @property
    def links_to(self):
        if self.accordion_children:
            return ""
        output = ""
        direct_modeling_object_attributes_attr_names = self.modeling_object_attr_names
        for modeling_object_web in [getattr(self, name) for name in direct_modeling_object_attributes_attr_names]:
            for mirrored_card in modeling_object_web.mirrored_cards:
                output += f"|{mirrored_card.web_id}"
        return output

    @property
    def data_line_opt(self):
        return "object-to-object"

    @property
    def data_attributes_as_list_of_dict(self):
        return [{'id': f'{self.web_id}', 'data-link-to': self.links_to, 'data-line-opt': self.data_line_opt}]

    @property
    def efootprint_contextual_modeling_obj_containers(self):
        return self._modeling_obj.contextual_modeling_obj_containers

    @property
    def list_containers_and_attr_name_in_list_container(self) -> Tuple[List["ModelingObjectWeb"], Optional[str]]:
        list_containers = []
        attr_name_in_list_container = None
        for contextual_container in self.efootprint_contextual_modeling_obj_containers:
            attr_name = contextual_container.attr_name_in_mod_obj_container
            container = contextual_container.modeling_obj_container
            container_signature = get_init_signature_params(container.efootprint_class)
            annotation = container_signature[attr_name].annotation
            if get_origin(annotation) and get_origin(annotation) in (list, List):
                list_containers.append(self.model_web.get_web_object_from_efootprint_id(container.id))
                attr_name_in_list_container = attr_name

        return list_containers, attr_name_in_list_container

    @property
    def dict_containers_and_attr_name_in_dict_container(self) -> Tuple[List["ModelingObjectWeb"], Optional[str]]:
        dict_containers = []
        attr_name_in_dict_container = None
        for contextual_container in self.efootprint_contextual_modeling_obj_containers:
            dict_container = getattr(contextual_container, "dict_container", None)
            if dict_container is None:
                continue
            container = contextual_container.modeling_obj_container
            dict_containers.append(self.model_web.get_web_object_from_efootprint_id(container.id))
            attr_name_in_dict_container = contextual_container.attr_name_in_mod_obj_container

        return dict_containers, attr_name_in_dict_container

    @property
    def mirrored_cards(self):
        """Recursively compute all mirrored instances based on rendered parent containers."""
        result = []
        list_containers, _ = self.list_containers_and_attr_name_in_list_container
        dict_containers, _ = self.dict_containers_and_attr_name_in_dict_container

        for container in list_containers:
            for container_mirror in container.mirrored_cards:
                result.append(type(self)(self._modeling_obj, self.model_web, list_container=container_mirror))
        for container in dict_containers:
            for container_mirror in container.mirrored_cards:
                result.append(type(self)(self._modeling_obj, self.model_web, dict_container=container_mirror))

        if not result:
            return [self]

        return result

    @property
    def parent_container(self):
        return self.list_container or self.dict_container

    @property
    def accordion_parent(self):
        return self.parent_container

    @property
    def all_accordion_parents(self):
        list_parents = []
        parent = self.accordion_parent
        while parent:
            list_parents.append(parent)
            parent = parent.accordion_parent

        return list_parents

    @property
    def top_parent(self):
        if len(self.all_accordion_parents) == 0:
            return self
        else:
            return self.all_accordion_parents[-1]

    @property
    def list_attr_names(self):
        init_signature = get_init_signature_params(self.efootprint_class)
        list_attr_names = []
        for attr_name, param_info in init_signature.items():
            annotation = param_info.annotation
            if get_origin(annotation) and get_origin(annotation) in (list, List):
                list_attr_names.append(attr_name)
        return list_attr_names

    @property
    def dict_attr_names(self):
        init_signature = get_init_signature_params(self.efootprint_class)
        dict_attr_names = []
        for attr_name, param_info in init_signature.items():
            annotation_origin = get_origin(param_info.annotation)
            if isinstance(annotation_origin, type) and issubclass(annotation_origin, ExplainableObjectDict):
                dict_attr_names.append(attr_name)
        return dict_attr_names

    @property
    def modeling_object_attr_names(self):
        init_signature = get_init_signature_params(self.efootprint_class)
        mod_obj_attr_names = []
        for attr_name, param_info in init_signature.items():
            annotation = param_info.annotation
            if not get_origin(annotation) and issubclass(annotation, ModelingObject):
                mod_obj_attr_names.append(attr_name)
        return mod_obj_attr_names

    @property
    def accordion_children(self):
        """Automatically compute accordion children from list and dict container attributes."""
        from model_builder.domain.efootprint_to_web_mapping import wrap_efootprint_object

        children = []
        for attr_name in self.list_attr_names:
            attr_value = getattr(self, attr_name, None)
            if attr_value and isinstance(attr_value, list):
                children.extend(attr_value)
        for attr_name in self.dict_attr_names:
            attr_value = self.get_efootprint_value(attr_name)
            if attr_value and isinstance(attr_value, dict):
                children.extend([
                    wrap_efootprint_object(child, self.model_web, dict_container=self)
                    for child in attr_value.keys()
                    if isinstance(child, ModelingObject)
                ])

        return children

    @property
    def child_attr_names_to_child_types_str(self) -> Dict[str, str]:
        """Child relationship attributes (list or ExplainableObjectDict) mapped to their child type string."""
        init_signature = get_init_signature_params(self.efootprint_class)
        child_attrs = {}
        for attr_name in self.list_attr_names + self.dict_attr_names:
            type_arg = get_args(init_signature[attr_name].annotation)[0]
            child_attrs[attr_name] = type_arg if isinstance(type_arg, str) else type_arg.__name__
        return child_attrs

    @property
    def child_object_types_str(self) -> List[str]:
        """Type strings of child objects (supports multiple child attributes)."""
        return list(self.child_attr_names_to_child_types_str.values())

    @property
    def child_object_type_str(self) -> str:
        """Retained for backward compatibility when there is a single child type."""
        child_types = self.child_object_types_str
        assert len(child_types) == 1, (
            f"{self} exposes multiple child types: {child_types}. Use child_object_types_str instead.")
        return child_types[0]

    @property
    def child_sections(self):
        """Structured view of children grouped by their child attribute/type."""
        from model_builder.domain.efootprint_to_web_mapping import (
            EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING, wrap_efootprint_object)

        dict_attr_names = self.dict_attr_names
        constraints = getattr(self.model_web, "creation_constraints", {})
        sections = []
        for attr_name, child_type in self.child_attr_names_to_child_types_str.items():
            if attr_name in dict_attr_names:
                children = [
                    wrap_efootprint_object(child, self.model_web, dict_container=self)
                    for child in (self.get_efootprint_value(attr_name) or {})
                    if isinstance(child, ModelingObject)]
            else:
                children = getattr(self, attr_name, []) or []
            linked_ids = {child.efootprint_id for child in children}
            all_of_type = self.model_web.get_efootprint_objects_from_efootprint_type(child_type)
            linkable_existing_count = sum(1 for obj in all_of_type if obj.id not in linked_ids)

            web_class = EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING.get(child_type)
            if web_class and hasattr(web_class, "can_create"):
                defining_class = next(c for c in web_class.__mro__ if "can_create" in c.__dict__)
                constraint_key = defining_class.__name__
                disabled = not constraints.get(constraint_key, {}).get("enabled", True)
            else:
                constraint_key = ""
                disabled = False

            sections.append({
                "type_str": child_type,
                "children": children,
                "attr_name": attr_name,
                "linkable_existing_count": linkable_existing_count,
                "disabled": disabled,
                "constraint_key": constraint_key,
            })

        return sections

    def self_delete(self):
        obj_type = self.class_as_simple_str
        object_id = self.efootprint_id
        cascade_children_to_delete_before_cache_removal = []
        for modeling_obj in self.mod_obj_attributes:
            if (
                modeling_obj.gets_deleted_if_unique_mod_obj_container_gets_deleted
                and len(modeling_obj.modeling_obj_containers) == 1
            ):
                cascade_children_to_delete_before_cache_removal.append(modeling_obj)
        logger.info(f"Deleting {self.name}")
        self.modeling_obj.self_delete()
        for mod_obj in cascade_children_to_delete_before_cache_removal:
            mod_obj.self_delete()
        self.model_web.response_objs[obj_type].pop(object_id, None)
        self.model_web.flat_efootprint_objs_dict.pop(object_id, None)
