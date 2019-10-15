from .grammar import grammar
from .visitor import JSCNVisitor
from .tree import Type
from typing import Any


__version__ = "0.5"


def _parse(what: str, source: str, verbose=False) -> Any:
    raw_tree = grammar[what].parse(source)
    if verbose:
        print("Raw output:", raw_tree)
    visitor = JSCNVisitor()
    parsed_tree = visitor.visit(raw_tree)
    if verbose:
        print("Parsed output:", parsed_tree)
    return parsed_tree


def Schema(source: str, verbose=False) -> tree.Schema:
    return _parse('schema', source)


def Definitions(source: str, verbose=False) -> tree.Definitions:
    return _parse('definitions', source)
