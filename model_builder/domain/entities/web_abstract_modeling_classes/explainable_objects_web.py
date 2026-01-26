import string
from typing import Tuple, List, Dict, Type

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity

from model_builder.domain.entities.web_abstract_modeling_classes.object_linked_to_modeling_obj_web import ObjectLinkedToModelingObjWeb


class ExplainableObjectWeb(ObjectLinkedToModelingObjWeb):
    def compute_literal_formula_and_ancestors_mapped_to_symbols_list(self) \
        -> Tuple[List[str|Type["ExplainableObjectWeb"]], List[Dict[str, Type["ExplainableObjectWeb"]]]]:
        # Base symbols: Roman lowercase + Greek lowercase
        base_symbols = list(string.ascii_lowercase) + [
            'α', 'β', 'γ', 'δ', 'ε', 'ζ', 'η', 'θ', 'ι', 'κ', 'λ', 'μ', 'ν', 'ξ', 'ο', 'π', 'ρ', 'σ', 'τ', 'υ', 'φ',
            'χ', 'ψ', 'ω']

        def get_symbol(i: int) -> str:
            n = len(base_symbols)
            index = i % n
            cycle = i // n
            base = base_symbols[index]
            return base if cycle == 0 else f"{base}{cycle}"

        ancestor_ids_to_symbols_mapping = {}
        ids_to_ancestors_mapping = {}
        if isinstance(self.efootprint_object.explain_nested_tuples_from_json, tuple):
            # For some reason, redis or local memory cache returns a tuple instead of a list
            self.efootprint_object.explain_nested_tuples_from_json = list(self.efootprint_object.explain_nested_tuples_from_json)
        flat_tuple_formula = self.compute_formula_as_flat_tuple(self.explain_nested_tuples)
        literal_formula = []
        current_symbol_index = 0
        for elt in flat_tuple_formula:
            if isinstance(elt, ExplainableObject):
                web_wrapper = ExplainableQuantityWeb if isinstance(elt, ExplainableQuantity) else ExplainableObjectWeb
                if elt.modeling_obj_container is None:
                    literal_formula.append(
                        {"symbol": elt.label,
                         "explainable_object_web": web_wrapper(elt, self.model_web)})
                elif elt.id in ancestor_ids_to_symbols_mapping:
                    literal_formula.append(
                        {"symbol": ancestor_ids_to_symbols_mapping[elt.id],
                         "explainable_object_web": web_wrapper(elt, self.model_web)})
                else:
                    ancestor_ids_to_symbols_mapping[elt.id] = get_symbol(current_symbol_index)
                    literal_formula.append(
                        {"symbol": ancestor_ids_to_symbols_mapping[elt.id],
                         "explainable_object_web": web_wrapper(elt, self.model_web)})
                    current_symbol_index += 1
                    ids_to_ancestors_mapping[elt.id] = elt
            else:
                literal_formula.append(elt)

        ancestors_mapped_to_symbols_list = []

        for ancestor_id in ids_to_ancestors_mapping:
            ancestor = ids_to_ancestors_mapping[ancestor_id]
            web_wrapper = ExplainableQuantityWeb if isinstance(ancestor, ExplainableQuantity) else ExplainableObjectWeb
            ancestors_mapped_to_symbols_list.append(
                {"symbol": ancestor_ids_to_symbols_mapping[ancestor_id],
                 "explainable_object_web": web_wrapper(ancestor, self.model_web)})

        return literal_formula, ancestors_mapped_to_symbols_list

    def web_children(self):
        web_children = []
        for child in self.direct_children_with_id:
            assert child.modeling_obj_container is not None
            web_wrapper = ExplainableQuantityWeb if isinstance(child, ExplainableQuantity) else ExplainableObjectWeb
            web_children.append(web_wrapper(child, self.model_web))

        return web_children


class ExplainableQuantityWeb(ExplainableObjectWeb):
    @property
    def rounded_value(self):
        return round(self.value, 2)

    @property
    def unit(self):
        return self.value.units


class ExplainableObjectDictWeb(ObjectLinkedToModelingObjWeb):
    @property
    def get_values_as_list(self) -> List[ExplainableObjectWeb]:
        return [ExplainableObjectWeb(explainable_object, self.model_web)
                for explainable_object in self.efootprint_object.values()]
