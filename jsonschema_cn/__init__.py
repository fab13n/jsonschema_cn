from .grammar import grammar
from .visitor import JSCNVisitor
from .tree import Type
from typing import Any


__version__ = "0.1"


def to_tree(source: str) -> Type:
    raw_tree = grammar.parse(source)
    visitor = JSCNVisitor()
    parsed_tree = visitor.visit(raw_tree)
    return parsed_tree


def to_schema(source: str) -> Any:
    return to_tree(source).to_schema()


def to_json(source: str) -> str:
    return to_tree(source).to_json()
