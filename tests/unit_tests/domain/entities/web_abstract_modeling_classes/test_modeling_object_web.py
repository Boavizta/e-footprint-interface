"""Unit tests for ModelingObjectWeb.

These tests cover entity-specific behavior (attribute delegation, protection
against setting wrapped objects, child/list helpers, and web id formatting).
"""

from typing import List
from unittest.mock import MagicMock

import pytest

from model_builder.domain.entities.web_abstract_modeling_classes import modeling_object_web
from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb
from model_builder.domain.entities.web_abstract_modeling_classes.object_linked_to_modeling_obj_web import (
    ObjectLinkedToModelingObjWeb,
)


class StubModelingObject:
    """Lightweight stand-in for efootprint ModelingObject used in tests."""

    def __init__(self, id_: str = "stub-id", class_name: str = "Stub", **extra_attrs):
        object.__setattr__(self, "id", id_)
        object.__setattr__(self, "class_as_simple_str", class_name)
        object.__setattr__(self, "values", {})
        object.__setattr__(self, "efootprint_class", type(self))
        for key, value in extra_attrs.items():
            object.__setattr__(self, key, value)

    def __setattr__(self, key, value, check_input_validity=True):  # pragma: no cover - exercised via wrapper
        if key not in {"id", "class_as_simple_str", "values", "efootprint_class"}:
            self.values[key] = value
        object.__setattr__(self, key, value)


class TestModelingObjectWeb:
    """Tests for ModelingObjectWeb behavior."""

    # --- __getattr__ ---

    def test_getattr_preserves_property_error_instead_of_fallback(self):
        """Property errors on subclass should propagate, not fall back to _modeling_obj."""

        class ChildThatRaises(ModelingObjectWeb):
            @property
            def web_id(self):  # pragma: no cover - behavior tested via exception path
                raise PermissionError("no web_id")

        wrapper = ChildThatRaises(StubModelingObject(), MagicMock())

        with pytest.raises(PermissionError, match="no web_id"):
            _ = wrapper.web_id

    def test_getattr_falls_back_to_modeling_obj_attribute(self):
        stub_model = StubModelingObject(extra_attr="domain_value")
        wrapper = ModelingObjectWeb(stub_model, MagicMock())

        assert wrapper.extra_attr == "domain_value"

    def test_getattr_blocks_id_access(self):
        stub_model = StubModelingObject()
        wrapper = ModelingObjectWeb(stub_model, MagicMock())

        with pytest.raises(AttributeError, match="id attribute"):
            _ = wrapper.id

    # --- __setattr__ ---

    def test_setattr_allows_settable_attributes(self):
        wrapper = ModelingObjectWeb(StubModelingObject(), MagicMock())
        new_model_web = MagicMock()

        wrapper.model_web = new_model_web

        assert wrapper.model_web is new_model_web

    def test_setattr_blocks_unknown_attributes(self):
        wrapper = ModelingObjectWeb(StubModelingObject(), MagicMock())

        with pytest.raises(PermissionError):
            wrapper.some_new_attr = "nope"

    # --- set_efootprint_value ---

    def test_set_efootprint_value_blocks_wrapped_objects(self):
        base_model = StubModelingObject()
        wrapper = ModelingObjectWeb(base_model, MagicMock())
        other_wrapper = ModelingObjectWeb(StubModelingObject("other", "Other"), MagicMock())

        with pytest.raises(PermissionError):
            wrapper.set_efootprint_value("child", other_wrapper)

        with pytest.raises(PermissionError):
            wrapper.set_efootprint_value("child_list", [other_wrapper])

        class DummyLinked(ObjectLinkedToModelingObjWeb):
            pass

        dummy_linked = object.__new__(DummyLinked)

        with pytest.raises(PermissionError):
            wrapper.set_efootprint_value("linked", dummy_linked)

    def test_set_efootprint_value_delegates_to_underlying_object(self):
        base_model = StubModelingObject()
        wrapper = ModelingObjectWeb(base_model, MagicMock())

        wrapper.set_efootprint_value("threshold", 42)

        assert base_model.values["threshold"] == 42

    # --- get_efootprint_value ---

    def test_get_efootprint_value_returns_attribute_or_none(self):
        stub_model = StubModelingObject(foo="bar")
        wrapper = ModelingObjectWeb(stub_model, MagicMock())

        assert wrapper.get_efootprint_value("foo") == "bar"
        assert wrapper.get_efootprint_value("missing") is None

    # --- calculated_attributes_values ---

    def test_calculated_attributes_values_use_modeling_obj_list(self):
        stub_model = StubModelingObject(calculated_attributes=["alpha", "beta"], alpha=1, beta=2)
        wrapper = ModelingObjectWeb(stub_model, MagicMock())

        assert wrapper.calculated_attributes_values == [1, 2]

    # --- equality + hash ---

    def test_equality_and_hash_use_web_id(self):
        wrapper_a = ModelingObjectWeb(StubModelingObject("id1", "Thing"), MagicMock())
        wrapper_b = ModelingObjectWeb(StubModelingObject("id1", "Thing"), MagicMock())
        wrapper_c = ModelingObjectWeb(StubModelingObject("id2", "Thing"), MagicMock())

        assert wrapper_a == wrapper_b
        assert wrapper_a != wrapper_c
        assert hash(wrapper_a) == hash(wrapper_b)

    # --- web_id ---

    def test_web_id_includes_list_container_when_present(self):
        parent = ModelingObjectWeb(StubModelingObject("p1", "Parent"), MagicMock())
        child = ModelingObjectWeb(StubModelingObject("c1", "Child"), MagicMock(), list_container=parent)

        assert child.web_id == "Child-c1_in_Parent-p1"

    # --- template_name ---

    def test_template_name_converts_to_snake_case(self):
        stub_model = StubModelingObject(class_name="EdgeUsagePattern")
        wrapper = ModelingObjectWeb(stub_model, MagicMock())

        assert wrapper.template_name == "edge_usage_pattern"

    # --- links_to ---

    def test_links_to_direct_modeling_objects(self, monkeypatch):
        stub_model = StubModelingObject()
        model_web = MagicMock()
        obj_a = StubModelingObject(id_="a")
        obj_b = StubModelingObject(id_="b")
        model_web.get_web_object_from_efootprint_id.side_effect = [
            MagicMock(web_id="web-a"),
            MagicMock(web_id="web-b"),
        ]

        def fake_get_instance_attributes(obj, target_class):
            if target_class.__name__ == "ModelingObject":
                return {"a": obj_a, "b": obj_b}
            return {}

        monkeypatch.setattr(modeling_object_web, "get_instance_attributes", fake_get_instance_attributes)
        wrapper = ModelingObjectWeb(stub_model, model_web)

        assert wrapper.links_to == "|web-a|web-b"

    def test_links_to_list_modeling_objects(self, monkeypatch):
        stub_model = StubModelingObject()
        model_web = MagicMock()
        obj_a = StubModelingObject(id_="a")
        obj_b = StubModelingObject(id_="b")
        model_web.get_web_object_from_efootprint_id.side_effect = [
            MagicMock(links_to="link-a"),
            MagicMock(links_to="link-b"),
        ]

        def fake_get_instance_attributes(obj, target_class):
            if target_class.__name__ == "ListLinkedToModelingObj":
                return {"items": [obj_a, obj_b]}
            return {}

        monkeypatch.setattr(modeling_object_web, "get_instance_attributes", fake_get_instance_attributes)
        wrapper = ModelingObjectWeb(stub_model, model_web)

        assert wrapper.links_to == "|link-a|link-b"

    # --- data_attributes_as_list_of_dict ---

    def test_data_attributes_as_list_of_dict_uses_links_and_line_opt(self):
        class CustomWrapper(ModelingObjectWeb):
            @property
            def links_to(self):
                return "target"

        wrapper = CustomWrapper(StubModelingObject("x1", "Sample"), MagicMock())

        assert wrapper.data_attributes_as_list_of_dict == [
            {"id": "Sample-x1", "data-link-to": "target", "data-line-opt": "object-to-object"}
        ]

    # --- list containers / mirrored cards ---

    def test_list_containers_and_attr_name_in_list_container(self):
        class ContainerSig:  # pragma: no cover - only signature used
            def __init__(self, items: List[int], label: str):
                self.items = items
                self.label = label

        class ContextualContainer:
            def __init__(self, attr_name_in_mod_obj_container, modeling_obj_container):
                self.attr_name_in_mod_obj_container = attr_name_in_mod_obj_container
                self.modeling_obj_container = modeling_obj_container

        container_obj = StubModelingObject(id_="c1", class_name="Container", efootprint_class=ContainerSig)
        non_list_container = StubModelingObject(id_="c2", class_name="Other", efootprint_class=ContainerSig)
        contextual_containers = [
            ContextualContainer("items", container_obj),
            ContextualContainer("label", non_list_container),
        ]
        stub_model = StubModelingObject(contextual_modeling_obj_containers=contextual_containers)
        model_web = MagicMock()
        model_web.get_web_object_from_efootprint_id.return_value = MagicMock(web_id="container-web")

        wrapper = ModelingObjectWeb(stub_model, model_web)
        list_containers, attr_name = wrapper.list_containers_and_attr_name_in_list_container

        assert len(list_containers) == 1
        assert list_containers[0].web_id == "container-web"
        assert attr_name == "items"

    def test_mirrored_cards_returns_self_when_no_list_containers(self):
        stub_model = StubModelingObject(contextual_modeling_obj_containers=[])
        wrapper = ModelingObjectWeb(stub_model, MagicMock())

        assert wrapper.mirrored_cards == [wrapper]

    def test_mirrored_cards_returns_mirrors_for_list_containers(self):
        class MirroredWrapper(ModelingObjectWeb):
            @property
            def list_containers_and_attr_name_in_list_container(self):
                return [self._list_container], "items"

        stub_model = StubModelingObject()
        list_container = MagicMock()
        mirror_container = MagicMock()
        list_container.mirrored_cards = [mirror_container]
        wrapper = MirroredWrapper(stub_model, MagicMock())
        object.__setattr__(wrapper, "_list_container", list_container)

        mirrored = wrapper.mirrored_cards

        assert len(mirrored) == 1
        assert mirrored[0].list_container is mirror_container

    # --- accordion hierarchy ---

    def test_all_accordion_parents_and_top_parent(self):
        top = ModelingObjectWeb(StubModelingObject("top", "Top"), MagicMock())
        mid = ModelingObjectWeb(StubModelingObject("mid", "Mid"), MagicMock(), list_container=top)
        leaf = ModelingObjectWeb(StubModelingObject("leaf", "Leaf"), MagicMock(), list_container=mid)

        assert leaf.all_accordion_parents == [mid, top]
        assert leaf.top_parent == top

    # --- children helpers ---

    def test_children_property_name_requires_single_list_attribute(self):
        class Container:  # pragma: no cover - only signature used
            def __init__(self, items: List[int]):
                self.items = items

        base_model = StubModelingObject(efootprint_class=Container)
        wrapper = ModelingObjectWeb(base_model, MagicMock())

        assert wrapper.children_property_name == "items"

    def test_list_attr_names_and_accordion_children(self):
        class Container:  # pragma: no cover - only signature used
            def __init__(self, items: List[int], tags: List[str], name: str):
                self.items = items
                self.tags = tags
                self.name = name

        stub_model = StubModelingObject(
            efootprint_class=Container,
            items=[1, 2],
            tags=["a"],
            name="ignore",
        )
        wrapper = ModelingObjectWeb(stub_model, MagicMock())

        assert wrapper.list_attr_names == ["items", "tags"]
        assert wrapper.accordion_children == [1, 2, "a"]

    def test_child_sections_returns_types_and_children(self):
        class Foo:
            pass

        class Bar:
            pass

        class Container:  # pragma: no cover - only signature used
            def __init__(self, foos: List[Foo], bars: List[Bar]):
                self.foos = foos
                self.bars = bars

        foos = [Foo(), Foo()]
        bars = [Bar()]
        base_model = StubModelingObject(
            efootprint_class=Container,
            foos=foos,
            bars=bars,
        )
        wrapper = ModelingObjectWeb(base_model, MagicMock())

        sections = wrapper.child_sections

        assert sections == [
            {"type_str": "Foo", "children": foos, "attr_name": "foos"},
            {"type_str": "Bar", "children": bars, "attr_name": "bars"},
        ]

    def test_child_object_types_str_and_type_str_validation(self):
        class Foo:
            pass

        class Bar:
            pass

        class Container:  # pragma: no cover - only signature used
            def __init__(self, foos: List[Foo], bars: List[Bar]):
                self.foos = foos
                self.bars = bars

        stub_model = StubModelingObject(efootprint_class=Container, foos=[], bars=[])
        wrapper = ModelingObjectWeb(stub_model, MagicMock())

        assert wrapper.child_object_types_str == ["Foo", "Bar"]
        with pytest.raises(AssertionError, match="multiple child types"):
            _ = wrapper.child_object_type_str

    # --- self_delete ---

    def test_self_delete_removes_objects_and_cascades(self):
        def make_child(name, should_delete, container_count):
            child = MagicMock()
            child.name = name
            child.gets_deleted_if_unique_mod_obj_container_gets_deleted = should_delete
            child.modeling_obj_containers = [object()] * container_count
            return child

        child_keep = make_child("keep", True, 2)
        child_delete = make_child("delete", True, 1)
        child_skip = make_child("skip", False, 1)

        stub_model = StubModelingObject(
            id_="obj1",
            class_name="Stub",
            name="Main",
            mod_obj_attributes=[child_keep, child_delete, child_skip],
        )
        stub_model.self_delete = MagicMock()
        model_web = MagicMock()
        model_web.response_objs = {"Stub": {"obj1": stub_model}}
        model_web.flat_efootprint_objs_dict = {"obj1": stub_model}
        wrapper = ModelingObjectWeb(stub_model, model_web)

        wrapper.self_delete()

        assert "obj1" not in model_web.response_objs["Stub"]
        assert "obj1" not in model_web.flat_efootprint_objs_dict
        stub_model.self_delete.assert_called_once()
        child_delete.self_delete.assert_called_once()
        child_keep.self_delete.assert_not_called()
        child_skip.self_delete.assert_not_called()
