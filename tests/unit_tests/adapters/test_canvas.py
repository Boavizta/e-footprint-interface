from model_builder.adapters.canvas import has_canvas_card


def test_canvas_placement_distinguishes_roots_nested_children_and_references(minimal_model_web):
    model = minimal_model_web
    pattern = model.usage_patterns[0]
    journey = model.usage_journeys[0]
    server = model.servers[0]

    assert all(has_canvas_card(obj) for obj in (pattern, journey, server, model.jobs[0]))
    assert not has_canvas_card(server.storage)
    assert not has_canvas_card(pattern.devices[0])
    assert not has_canvas_card(model.system)
