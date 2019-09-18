from parsimonious import NodeVisitor
from collections import Sequence

from . import tree as T

class JSCNVisitor(NodeVisitor):

    SHELL_EXPRESSIONS = {
        "entry": 0, "type": 0, "litteral": 0,
        "cardinal": 1, "card_content": 0,
        "card_1": (0, 0), "card_2": (0, -1),
        "object": 0, "object_field": 0, "field_type": 0,
        "multiple": 1,
        "array": 0
    }

    def visit_string(self, node, c):
        _, cardinal = c
        return T.String(cardinal)

    def visit_integer(self, node, c):
        _, cardinal, multiple = c
        return T.Integer(cardinal, multiple)

    def visit_litteral(self, node, c):
        return T.Litteral(node.children[0].text)

    def visit_opt_multiple(self, node, c):
        return None if len(c) == 0 else c[0][1]

    def visit_opt_cardinal(self, node, c):
        return (None, None) if len(c) == 0 else c[0][1]

    def visit_card_min(self, node, c):
        return (c[0], None)

    def visit_card_max(self, node, c):
        return (None, c[2])

    def visit_int(self, node, c):
        return int(node.text)

    def visit_object_empty(self, node, c):
        return T.Object(())

    def visit_object_non_empty(self, node, c):
        _, first_field, other_fields_with_commas, _ = c
        other_fields = (item[1] for item in other_fields_with_commas)
        fields = (first_field, *other_fields)
        return T.Object(fields)

    def visit_field_pair(self, node, c):
        key, question, _, val = c
        return (key, bool(question), val)

    def visit_keyless_pair(self, node, c):
        return (None, True, c[2])

    def visit_dots(self, node, c):
        return None

    def visit_key(self, node, c):
        # TODO handle quote escapes
        return node.text[1:-1]

    def visit_array_empty(self, node, c):
        card = c[4]
        return T.ArrayList([], True, card)

    def visit_array_non_empty(self, node, c):
        _, first_type, other_types_with_commas, extra, _, card = c

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

    def visit_array_extra(self, node, c):
        if len(c) == 0:
            return None
        t = node.children[0].text
        if t.endswith("..."):
            return "..."
        else:
            return t

    def generic_visit(self, node, c):
        """ The generic visit method. """
        n = self.SHELL_EXPRESSIONS.get(node.expr_name)
        if n is None:
            return tuple(c)
        elif isinstance(n, Sequence):
            return tuple(c[i] for i in n)
        elif isinstance(n, int):
            return c[n]
        else:
            raise ValueError(f"bad SHELL_EXPRESSIONS for {node.expr_name}")
