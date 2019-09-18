import json

from .grammar import grammar
from .visitor import JSCNVisitor


def tojson(source: str) -> str:
    raw_tree = grammar.parse(source)
    visitor = JSCNVisitor()
    parsed_tree = visitor.visit(raw_tree)
    struct = parsed_tree.tojson()
    return json.dumps(struct)
