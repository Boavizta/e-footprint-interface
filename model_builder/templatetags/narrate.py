"""The calls of ``model_builder.narrate`` for a template. ``{% load narrate %}``, then, one tag a line:

    {% narrate "sentence" key=value … %}
    {% event "sentence" key=value … %}
    {% planned "<feature>#<slug>" "clause" key=value … expect key=value … %}
    {% evidence "<feature>#<slug>" "what is seen here today" key=value … expect key=value … %}

A tag renders nothing. Its pairs are its watch, and those after ``expect`` what the place should see, a key of
the watch each: both are resolved only when a test run collects, in the context the tag is rendered in. The
source index reads the tags as sites of the template (``comprehension_harness/python/source_index.py``).
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
    def __init__(self, call, tag, sentence, watch, expect, file, line):
        self.call, self.tag, self.sentence, self.watch, self.expect = call, tag, sentence, watch, expect
        self.file, self.line = file, line

    def render(self, context):
        def reader(pairs):
            return (lambda: {key: value.resolve(context) for key, value in pairs.items()}) if pairs else None

        calls.template_call(self.call, self.file, self.line, self.sentence, reader(self.watch), self.tag,
                            reader(self.expect))
        return ""


def _compile(parser, token):
    call, *words = token.split_contents()
    literals = 2 if call in TAGGED else 1
    if len(words) < literals:
        raise template.TemplateSyntaxError(f"{{% {call} %}} takes {'its tag and ' if literals == 2 else ''}its sentence")
    said = [_said(word, call) for word in words[:literals]]
    pairs = words[literals:]
    cut = pairs.index("expect") if "expect" in pairs else len(pairs)

    def compiled(some) -> dict:
        read = {}
        for pair in some:
            key, separator, expression = pair.partition("=")
            if not separator or not key.isidentifier() or not expression:
                raise template.TemplateSyntaxError(f"{{% {call} %}} gives its watch as key=value pairs, not {pair}")
            read[key] = parser.compile_filter(expression)
        return read

    return Call(call, said[0] if literals == 2 else None, said[-1], compiled(pairs[:cut]), compiled(pairs[cut + 1:]),
                parser.origin.name, token.lineno)


for name in ("narrate", "event", *TAGGED):
    register.tag(name, _compile)
