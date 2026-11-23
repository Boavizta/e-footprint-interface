"""The calls of ``model_builder.narrate`` for a template. ``{% load narrate %}``, then, one tag a line:

    {% narrate "sentence" key=value … %}
    {% event "sentence" key=value … %}
    {% planned "<feature>#<slug>" "clause" key=value … expect key="literal" … %}
    {% evidence "<feature>#<slug>" "what is seen here today" key=value … expect key="literal" … %}

A tag renders nothing. Its pairs are its watch, resolved only when a test run collects. What follows ``expect``
is what the place should see: the plan's page reads it from the source, and nothing reads it here. The source
index reads the tags as sites of the template (``comprehension_harness/python/source_index.py``).
"""
from django import template

from model_builder import narrate as calls

register = template.Library()
TAGGED = ("planned", "evidence")


def _said(word: str, call: str) -> str:
    if len(word) < 2 or word[0] != '"' or word[-1] != '"':
        raise template.TemplateSyntaxError(f"{{% {call} %}} opens with literal strings in double quotes, not {word}")
    return word[1:-1].replace('\\"', '"')


class Call(template.Node):
    def __init__(self, call, tag, sentence, watch, file, line):
        self.call, self.tag, self.sentence, self.watch, self.file, self.line = call, tag, sentence, watch, file, line

    def render(self, context):
        watch = (lambda: {key: value.resolve(context) for key, value in self.watch.items()}) if self.watch else None
        calls.template_call(self.call, self.file, self.line, self.sentence, watch, self.tag)
        return ""


def _compile(parser, token):
    call, *words = token.split_contents()
    literals = 2 if call in TAGGED else 1
    if len(words) < literals:
        raise template.TemplateSyntaxError(f"{{% {call} %}} takes {'its tag and ' if literals == 2 else ''}its sentence")
    said = [_said(word, call) for word in words[:literals]]
    pairs = words[literals:]
    watched = pairs[:pairs.index("expect")] if "expect" in pairs else pairs
    watch = {}
    for pair in watched:
        key, separator, expression = pair.partition("=")
        if not separator or not key.isidentifier() or not expression:
            raise template.TemplateSyntaxError(f"{{% {call} %}} gives its watch as key=value pairs, not {pair}")
        watch[key] = parser.compile_filter(expression)
    return Call(call, said[0] if literals == 2 else None, said[-1], watch, parser.origin.name, token.lineno)


for name in ("narrate", "event", *TAGGED):
    register.tag(name, _compile)
