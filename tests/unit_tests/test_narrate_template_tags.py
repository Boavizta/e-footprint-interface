"""The calls a template makes (``model_builder/templatetags/narrate.py``): what each tag hands the calls module."""
import pytest
from django.template import Context, Template, TemplateSyntaxError

from model_builder.templatetags import narrate as tags

TEMPLATE = '''{% load narrate %}<ul>
{% for row in rows %}
  <li>{% evidence "gift-cards#card-row" "A card is drawn **as a plain row**." drawn_as="ROW" expect drawn_as=row.kind|upper %}</li>
{% endfor %}
{% narrate "The list is **closed**." %}
{% planned "gift-cards#card-row:row-id" "The row\'s id is the card\'s." id=rows|length distinct id expect id=1 %}
{% built "gift-cards#card-row:row-class" %}
</ul>'''


def test_a_tag_renders_nothing_and_hands_its_call_with_where_it_is_written(monkeypatch):
    handed = []

    def collect(call, file, line, sentence, watch, tag, expect):
        # A collector reads the watch, and what the place should see, as the call is made: the tag's context is
        # the one it is rendered in.
        handed.append((call, line, sentence, watch() if watch else None, tag, expect() if expect else None))

    monkeypatch.setattr(tags.calls, "template_call", collect)

    rendered = Template(TEMPLATE).render(Context({"rows": [{"kind": "card"}, {"kind": "cash"}]}))

    assert "".join(rendered.split()) == "<ul><li></li><li></li></ul>"
    # What follows `expect` is what the row should be drawn as: its own kind, at each crossing.
    evidence = ("evidence", 3, "A card is drawn **as a plain row**.", {"drawn_as": "ROW"}, "gift-cards#card-row")
    # The keys after `distinct` are the source index's to read: the call is handed the watch and what it expects.
    assert handed == [(*evidence, {"drawn_as": "CARD"}), (*evidence, {"drawn_as": "CASH"}),
                      ("narrate", 5, "The list is **closed**.", None, None, None),
                      ("planned", 6, "The row's id is the card's.", {"id": 2}, "gift-cards#card-row:row-id", {"id": 1}),
                      # A built tag says its place alone: no sentence, no watch.
                      ("built", 7, "", None, "gift-cards#card-row:row-class", None)]


@pytest.mark.parametrize("tag, said", [
    ("{% narrate sentence %}", "opens with literal strings in double quotes"),
    ('{% planned "gift-cards#card-row" %}', "takes its tag and its sentence"),
    ('{% built "gift-cards#card-row:row-id" "A change." %}', "takes one literal"),
    ("{% built %}", "takes one literal"),
    ('{% narrate "A step." kind %}', "gives its watch as key=value pairs"),
    ('{% planned "gift-cards#card-row" "A change." id=row.id distinct kind %}', "names after distinct keys of its watch"),
])
def test_a_tag_that_does_not_have_the_shape_fails_the_template(tag, said):
    with pytest.raises(TemplateSyntaxError, match=said):
        Template("{% load narrate %}" + tag)
