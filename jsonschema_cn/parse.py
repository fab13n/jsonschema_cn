from .unspace import UnspaceVisitor
from .peg_visitor import TreeBuildingVisitor
from . import grammar
from . import tree as T
from parsimonious.exceptions import ParseError

jscn_visitor = TreeBuildingVisitor()
unspace_visitor = UnspaceVisitor()


def parse(what: str, source: str, verbose=False) -> T.Type:
    try:
        raw_tree = grammar[what].parse(source)
    except ParseError as e:
        raise ValueError(f"Invalid JSCN syntax line {e.line()} column {e.column()} (rule {e.expr.name})") from None

    unspaced_tree = unspace_visitor.visit(raw_tree)
    if verbose:
        print("PEG tree:\n" + unspaced_tree.prettily())
    parsed_tree = jscn_visitor.visit(unspaced_tree)
    if verbose:
        print("JSCN tree:\n" + parsed_tree.prettily())
    parsed_tree.source = source
    return parsed_tree
