from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.constants.units import u

from model_builder.adapters.forms.form_field_generator import generate_dynamic_form


def _get_field_by_web_id(fields: list[dict], web_id: str) -> dict:
    return next(field for field in fields if field["web_id"] == web_id)


def test_generate_dynamic_form_preserves_imported_decimal_precision(minimal_model_web):
    server = minimal_model_web.servers[0].modeling_obj
    server.power = ExplainableQuantity(250.37 * u.W, label="power")

    _, advanced_fields, _ = generate_dynamic_form("Server", server.__dict__, minimal_model_web)

    power_field = _get_field_by_web_id(advanced_fields, "Server_power")

    assert power_field["default"] == "250.37"
    assert power_field["step"] == "0.01"


def test_generate_dynamic_form_keeps_integer_step_for_integral_values(minimal_model_web):
    server = minimal_model_web.servers[0].modeling_obj
    server.power = ExplainableQuantity(250 * u.W, label="power")

    _, advanced_fields, _ = generate_dynamic_form("Server", server.__dict__, minimal_model_web)

    power_field = _get_field_by_web_id(advanced_fields, "Server_power")

    assert power_field["default"] == "250"
    assert power_field["step"] == "1"
