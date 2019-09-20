from parsimonious import NodeVisitor
from collections import Sequence
from typing import Tuple, Optional
import json

from . import tree as T


class JSCNVisitor(NodeVisitor):

    WHITESPACE_TOKEN = object()

    SHELL_EXPRESSIONS = {
        "type": 0,
        "card_content": 0,
        "card_1": (0, 0),
        "card_2": (0, -1),
        "object": 0,
        "object_property": 0,
        "object_pair_type": 0,
        "object_pair_name": 0,
        "array": 0,
        "parens": 1,
    }

    @classmethod
    def unspace(cls, sequence, index=None):
        """Remove space tokens from a sequence of visited children.
        if extra integer indexes are passed as args, only keep those."""
        unspaced = tuple(x for x in sequence if x is not cls.WHITESPACE_TOKEN)
        if index is not None:
            return unspaced[index]
        else:
            return unspaced

    def visit__(self, node, c) -> object:
        return self.WHITESPACE_TOKEN

    def visit_entry(self, node, c) -> T.Entry:
        return T.Entry(self.unspace(c, 0))

    def visit_sequence_and(self, node, c) -> T.Type:
        first, rest = self.unspace(c)
        if len(rest):
            return T.Operator("allOf", first, *(item[1] for item in rest))
        else:
            return first

    def visit_sequence_or(self, node, c) -> T.Type:
        first, rest = self.unspace(c)
        if len(rest) == 0:
            return first
        args = [first] + [item[1] for item in rest]
        if all(isinstance(a, T.Constant) for a in args):
            # Convert oneof(const(...)...) into enum(...)
            constants = [a.args[0] for a in args]
            return T.Enum(*constants)
        else:
            return T.Operator("oneOf", first, *(item[1] for item in rest))

    def visit_string(self, node, c) -> T.String:
        _, cardinal = self.unspace(c)
        return T.String(cardinal=cardinal)

    def visit_integer(self, node, c) -> T.Integer:
        _, cardinal, multiple = self.unspace(c)
        return T.Integer(cardinal=cardinal, multiple=multiple)

    def visit_litteral(self, node, c) -> T.Litteral:
        # This rule is space-free
        return T.Litteral(node.children[0].text)

    def visit_lit_string(self, node, c) -> str:
        # This rule is space-free
        source = node.text[1:-1]
        unescaped = source.encode("utf-8").decode("unicode_escape")
        return unescaped

    def visit_lit_regex(self, node, c) -> T.String:
        return T.String(regex=node.children[-1].text[1:-1])

    def visit_lit_format(self, node, c) -> T.String:
        return T.String(format=node.children[-1].text[1:-1])

    def visit_opt_multiple(self, node, c) -> Optional[int]:
        uc = self.unspace(c)
        return None if len(uc) == 0 else uc[0][1]

    def visit_opt_cardinal(self, node, c) -> Tuple[Optional[int], Optional[int]]:
        # generic_visit didn't detect card_1, probably due to some node optimization?
        if len(c) == 0:  # Empty cardinal
            return (None, None)
        uc = self.unspace(c[0], 1)
        if isinstance(uc, int):
            return (uc, uc)
        else:
            return uc

    def visit_card_min(self, node, c) -> Tuple[int, None]:
        return (self.unspace(c, 0), None)

    def visit_card_max(self, node, c) -> Tuple[None, int]:
        return (None, self.unspace(c, 2))

    def visit_lit_integer(self, node, c) -> int:
        # This rule is space-free
        text = node.text
        base = 16 if len(text) > 2 and text[1] == "x" else 10
        return int(text, base)
    
    def visit_constant(self, node, c) -> T.Constant:
        # This rule is space-free
        source = node.text[1:-1]
        try:
            value = json.loads(source)
            return T.Constant(value)
        except json.JSONDecodeError:
            raise ValueError(f"{source} is not a valid JSON fragment")

    def visit_object_empty(self, node, c) -> T.Object:
        return T.Object(additional_properties=True, cardinal=c[-1])

    def visit_object_non_empty(self, node, c) -> T.Object:
        _, first_field, others_with_commas, add_props, _, card = self.unspace(c)
        other_fields = (item[1] for item in others_with_commas)
        fields = (first_field, *other_fields)
        return T.Object(
            properties=fields, additional_properties=add_props, cardinal=card
        )

    def visit_object_pair(self, node, c) -> T.ObjectProperty:
        key, question, _, val = self.unspace(c)
        return T.ObjectProperty(key, bool(question), val)

    def visit_object_pair_unquoted_name(self, node, c) -> str:
        return node.text

    def visit_object_unnamed_pair(self, node, c) -> T.ObjectProperty:
        return T.ObjectProperty(None, True, self.unspace(c, 2))

    def visit_object_extra(self, node, c) -> str:
        return node.text.endswith("...")

    def visit_array_empty(self, node, c) -> T.Array:
        card = self.unspace(c, -1)
        return T.Array(types=[], additional_types=True, cardinal=card)

    def visit_array_non_empty(self, node, c) -> T.Array:
        _, first_type, other_types_with_commas, extra, _, card = self.unspace(c)

        other_types = (t[1] for t in other_types_with_commas)
        types = (first_type, *other_types)

        if extra is None:  # No suffix -> no extra items allowed
            additional_items = False
        elif extra == "...":
            additional_items = True
        elif extra == "+":
            additional_items = types[-1]
            # Don't remove it from required items, there must be at least one
        else:  # Last type is the type of extra items
            additional_items = types[-1]
            types = types[:-1]
        if isinstance(card[0], int) and len(types) >= card[0]:
            card = (None, card[1])  # Constraint is redundant
        if isinstance(card[1], int) and not additional_items and len(types) < card[1]:
            raise ValueError(
                f"An array cannot be both {len(types)} and <={card[1]} items long"
            )

        return T.Array(types=types, additional_types=additional_items, cardinal=card)

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
