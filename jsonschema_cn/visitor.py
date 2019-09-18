from parsimonious import NodeVisitor
from collections import Sequence
from typing import Tuple, Optional

from . import tree as T


class JSCNVisitor(NodeVisitor):

    WHITESPACE_TOKEN = object()

    SHELL_EXPRESSIONS = {
        "entry": 0, "type": 0, "litteral": 0,
        "cardinal": 1, "card_content": 0,
        "card_1": (0, 0), "card_2": (0, -1),
        "object": 0, "object_field": 0, "field_type": 0,
        "multiple": 1,
        "array": 0
    }

    @classmethod
    def unspace(cls, sequence, index=None):
        """Remove space tokens from a sequence of visited children.
        if extra integer indexes are passed as args, only keep those."""
        unspaced = tuple(item for item in sequence if item is not cls.WHITESPACE_TOKEN)
        if index is not None:
            return unspaced[index]
        else:
            return unspaced

    def visit__(self, node, c) -> object:
        return self.WHITESPACE_TOKEN

    def visit_string(self, node, c) -> T.String:
        _, cardinal = self.unspace(c)
        return T.String(cardinal)

    def visit_integer(self, node, c) -> T.Integer:
        _, cardinal, multiple = self.unspace(c)
        return T.Integer(cardinal, multiple)

    def visit_litteral(self, node, c) -> T.Litteral:
        # This rule is space-free
        return T.Litteral(node.children[0].text)

    def visit_opt_multiple(self, node, c) -> Optional[int]:
        return None if len(c) == 0 else unspace(c[0], 1)

    def visit_opt_cardinal(self, node, c) -> Tuple[Optional[int], Optional[int]]:
        return (None, None) if len(c) == 0 else unspace(c[0], 1)

    def visit_card_min(self, node, c) -> Tuple[int, None]:
        return (self.unspace(c, 0), None)

    def visit_card_max(self, node, c) -> Tuple[None, int]:
        return (None, self.unspace(c, 2))

    def visit_int(self, node, c) -> int:
        # This rule is space-free
        return int(node.text)

    def visit_object_empty(self, node, c) -> T.Object:
        return T.Object(())

    def visit_object_non_empty(self, node, c) -> T.Object:
        _, first_field, other_fields_with_commas, _ = self.unspace(c)
        other_fields = (item[1] for item in other_fields_with_commas)
        fields = (first_field, *other_fields)
        return T.Object(fields)

    def visit_field_pair(self, node, c) -> Tuple[str, bool, T.Node]:
        key, question, _, val = self.unspace(c)
        return (key, bool(question), val)

    def visit_property_less_pair(self, node, c) -> Tuple[None, bool, T.Node]:
        return (None, True, self.unspace(c, 2))

    def visit_object_property_name(self, node, c) -> str:
        # This rule is space-free
        # TODO handle quote escapes
        return node.text[1:-1]

    def visit_array_empty(self, node, c) -> T.Array:
        card = self.unspace(c, 4)
        return T.ArrayList([], True, card)

    def visit_array_non_empty(self, node, c) -> T.Array:
        _, first_type, other_types_with_commas, extra, _, card = self.unspace(c)

        other_types = (t[1] for t in other_types_with_commas)
        types = (first_type, *other_types)


        if extra is None:  # No ... / + / * -> no extra items allowed
            additional_items = False
        elif extra == "...":
            additional_items = True
        else:  # Last type is the type of extra items
            additional_items = types[-1]
            types = types[:-1]
            if extra == "+":  # There must be at least one extra item
                min_len = len(types) + 1
                if card[0] is None or card[0] < min_len:
                    card = (min_len, card[1])
        return T.Array(types, additional_items, card)

    def visit_array_extra(self, node, c) -> str:
        # This rule is space-free
        if len(c) == 0:
            return None
        t = node.children[0].text
        if t.endswith("..."):
            return "..."
        else:
            return t

    def generic_visit(self, node, c) -> tuple:
        """ The generic visit method. """
        n = self.SHELL_EXPRESSIONS.get(node.expr_name)
        unspaced_c = self.unspace(c)
        if n is None:
            return unspaced_c
        elif isinstance(n, Sequence):
            return tuple(unspaced_c[i] for i in n)
        elif isinstance(n, int):
            return unspaced_c[n]
        else:
            raise ValueError(f"bad SHELL_EXPRESSIONS for {node.expr_name}")
