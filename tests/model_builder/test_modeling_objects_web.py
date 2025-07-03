import unittest
from unittest.mock import patch, MagicMock, Mock

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject

from model_builder.modeling_objects_web import ExplainableObjectWeb


class TestExplainableObjectWebTestCase(unittest.TestCase):
    def test_compute_literal_formula_and_ancestors_mapped_to_symbols_list(self):
        # Arrange: create dummy EQ objects
        a = Mock(spec=ExplainableObject)
        b = Mock(spec=ExplainableObject)
        g = Mock(spec=ExplainableObject)
        a.id = "a"
        b.id = "b"
        g.id = "c"

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

        self.assertEqual(expected_formula, formula)
        self.assertEqual(expected_ancestors, ancestors_mapped)
