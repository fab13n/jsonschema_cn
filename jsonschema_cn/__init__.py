from .grammar import grammar
from .parse import parse
from .tree import Type
from .unspace import UnspaceVisitor
from typing import Any


__version__ = "0.28"


def Schema(source: str, verbose=False) -> tree.Schema:
    return parse("schema", source)


def Definitions(source: str, verbose=False) -> tree.Definitions:
    return parse("definitions", source)
