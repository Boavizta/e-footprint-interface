import unittest
from unittest.mock import patch, MagicMock, Mock

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject

from model_builder.web_abstract_modeling_classes.explainable_objects_web import ExplainableObjectWeb
from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class TestExplainableObjectWebTestCase(unittest.TestCase):
    def test_compute_literal_formula_and_ancestors_mapped_to_symbols_list(self):
        # Arrange: create dummy EQ objects
        a = Mock(spec=ExplainableObject)
        b = Mock(spec=ExplainableObject)
        g = Mock(spec=ExplainableObject)
        a.id = "a"
        b.id = "b"
        g.id = "c"
        a.modeling_obj_container = MagicMock()
        b.modeling_obj_container = MagicMock()
        g.modeling_obj_container = MagicMock()

        # Define the mocked return value of compute_formula_as_flat_tuple
        fake_flat_tuple = ("(", a, "+", b, ")", "*", g)

        obj = ExplainableObjectWeb(MagicMock(), MagicMock())

        with patch.object(obj, 'compute_formula_as_flat_tuple', return_value=fake_flat_tuple):
            formula, ancestors_mapped = obj.compute_literal_formula_and_ancestors_mapped_to_symbols_list()

        expected_formula = [
            "(",
            {"symbol": "a", "explainable_object": a},
            "+",
            {"symbol": "b", "explainable_object": b},
            ")",
            "*",
            {"symbol": "c", "explainable_object": g}
        ]

        expected_ancestors = [
            {"symbol": "a", "explainable_object": a},
            {"symbol": "b", "explainable_object": b},
            {"symbol": "c", "explainable_object": g}
        ]

        formula_error_msg = f"Expected formula: {expected_formula} but got formula: {formula}"
        for token_expected_formula, token_formula in zip(expected_formula, formula):
            if isinstance(token_expected_formula, str):
                self.assertEqual(token_expected_formula, token_formula, formula_error_msg)
            else:
                self.assertEqual(token_expected_formula["symbol"], token_formula["symbol"], formula_error_msg)
                self.assertEqual(token_expected_formula["explainable_object"],
                                 token_formula["explainable_object_web"].efootprint_object, formula_error_msg)
        ancestors_error_msg = f"Expected ancestors: {expected_ancestors} but got ancestors: {ancestors_mapped}"
        for token_expected_ancestor, token_ancestor in zip(expected_ancestors, ancestors_mapped):
            self.assertEqual(token_expected_ancestor["symbol"], token_ancestor["symbol"], ancestors_error_msg)
            self.assertEqual(token_expected_ancestor["explainable_object"],
                             token_ancestor["explainable_object_web"].efootprint_object, ancestors_error_msg)


class TestModelingObjectWebGetAttrTestCase(unittest.TestCase):
    def test_getattr_preserves_property_error_instead_of_falling_back_to_modeling_obj(self):
        """
        Test that when a property in a subclass raises an error, __getattr__ preserves that error
        instead of falling back to _modeling_obj and raising a different AttributeError.
        """
        # Arrange: create a mock modeling object and model_web
        mock_modeling_obj = Mock(spec=ModelingObject)
        mock_modeling_obj.id = "test_id"
        mock_model_web = MagicMock()

        class ModelingObjectChildThatRaisesAttributeError(ModelingObjectWeb):
            @property
            def web_id(self):
                raise PermissionError(
                    "You don't have a web_id attribute for ModelingObjectChildThatRaisesAttributeError")

        obj = ModelingObjectChildThatRaisesAttributeError(mock_modeling_obj, mock_model_web)

        # Act & Assert: accessing web_id should raise PermissionError, not AttributeError
        with self.assertRaises(PermissionError) as context:
            _ = obj.web_id

    def test_getattr_falls_back_to_modeling_obj_when_attribute_not_in_class(self):
        """
        Test that __getattr__ still properly falls back to _modeling_obj when the attribute
        doesn't exist in the web class hierarchy.
        """
        # Arrange
        mock_modeling_obj = Mock(spec=ModelingObject)
        mock_modeling_obj.some_domain_attribute = "domain_value"
        mock_model_web = MagicMock()

        obj = ModelingObjectWeb(mock_modeling_obj, mock_model_web)

        # Act
        result = obj.some_domain_attribute

        # Assert
        self.assertEqual(result, "domain_value")
