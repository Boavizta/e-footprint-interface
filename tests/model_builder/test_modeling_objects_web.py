import unittest
from unittest.mock import patch, MagicMock, Mock

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject

from model_builder.web_abstract_modeling_classes.explainable_objects_web import ExplainableObjectWeb


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
