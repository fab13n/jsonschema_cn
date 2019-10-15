from parsimonious import NodeVisitor
from collections import Sequence
from typing import Tuple, Optional, Set, Dict
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

    @staticmethod
    def gather_separated_list(first_item, other_items_with_separators) -> tuple:
        return (first_item, ) + tuple(item[1] for item in other_items_with_separators)

    def visit__(self, node, c) -> object:
        """Replace whitspaces with an easy-to-filter sentinel value."""
        return self.WHITESPACE_TOKEN

    def visit_schema(self, node, c) -> T.Schema:
        value, definitions = self.unspace(c)
        return T.Schema(value=value, definitions=definitions)

    def visit_sequence_and(self, node, c) -> T.Type:
        first, rest = self.unspace(c)
        if len(rest):
            values = (first, *(item[1] for item in rest))
            return T.Operator(operator="allOf", values=values)
        else:
            return first

    def visit_sequence_or(self, node, c) -> T.Type:
        first, rest = self.unspace(c)
        if len(rest) == 0:
            return first
        operands = self.gather_separated_list(first, rest)
        if all(isinstance(a, T.Constant) for a in operands):
            # Convert oneof(const(...)...) into enum(...)
            constants = [a.value for a in operands]
            return T.Enum(values=constants)
        else:
            return T.Operator(operator="oneOf", values=operands)

    def visit_not_type(self, node, c) -> T.Not:
        return T.Not(value=self.unspace(c, 1))

    def visit_string(self, node, c) -> T.String:
        _, cardinal = self.unspace(c)
        return T.String(cardinal=cardinal, format=None, regex=None)

    def visit_integer(self, node, c) -> T.Integer:
        _, cardinal, multiple = self.unspace(c)
        return T.Integer(cardinal=cardinal, multiple=multiple)

    def visit_litteral(self, node, c) -> T.Litteral:
        # This rule is space-free
        return T.Litteral(value=node.children[0].text)

    def visit_lit_string(self, node, c) -> str:
        # This rule is space-free
        source = node.text[1:-1]
        unescaped = source.encode("utf-8").decode("unicode_escape")
        return unescaped

    def visit_lit_regex(self, node, c) -> T.String:
        return T.String(format=None, cardinal=(None, None), regex=node.children[-1].text[1:-1])

    def visit_lit_format(self, node, c) -> T.String:
        return T.String(cardinal=(None, None), regex=None, format=node.children[-1].text[1:-1])

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
        else: # Pair of ints/nulls
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
            return T.Constant(value=value)
        except json.JSONDecodeError:
            raise ValueError(f"{source} is not a valid JSON fragment")

    def visit_object_keyword(self, node, c) -> T.Object:
        return T.Object(
            properties=[],
            additional_properties=True,
            property_names=None,
            cardinal=c[-1])

    def visit_object_empty(self, node, c) -> T.Object:
        kwargs = dict(
            properties=[],
            additional_properties=True,
            property_names=None)
        _, (only, only_regex), _, kwargs['cardinal'] = self.unspace(c)
        if not only:
            kwargs['additional_properties'] = True
        elif only_regex is not None:
            kwargs['additional_properties'] = True
            kwargs['property_names'] = only_regex
        else:
            kwargs['additional_properties'] = False
        return T.Object(**kwargs)

    def visit_object_non_empty(self, node, c) -> T.Object:
        _, (only, only_regex), first_field, other_fields, _, card = self.unspace(c)
        props = self.gather_separated_list(first_field, other_fields)
        kwargs = {'properties': props, 'cardinal': card, 'property_names': None}
        if not only:
            kwargs['additional_properties'] = True
        elif only_regex is not None:
            kwargs['additional_properties'] = True
            kwargs['property_names'] = only_regex
        else:
            kwargs['additional_properties'] = False
        return T.Object(**kwargs)

    def visit_object_pair(self, node, c) -> T.ObjectProperty:
        key, question, _, val = self.unspace(c)
        return T.ObjectProperty(key, bool(question), val)

    def visit_object_pair_unquoted_name(self, node, c) -> str:
        return node.text

    def visit_object_unnamed_pair(self, node, c) -> T.ObjectProperty:
        return T.ObjectProperty(None, True, self.unspace(c, 2))

    def visit_object_only(self, node, c) -> Tuple[bool, Optional[str]]:
        """Parse `only`, `only <pattern>` and `only <pattern>,`."""
        # TODO also `only <pattern>: <type>`
        if len(c) == 0:  # Empty sequence
            return False, None
        maybe_regex = self.unspace(c[0], 1)
        if len(maybe_regex):
            return True, maybe_regex[0][0]
        else:
            return True, None

    def visit_array_empty(self, node, c) -> T.Array:
        card = self.unspace(c, -1)
        return T.Array(items=[], additional_items=True, cardinal=card, unique=False)

    def visit_array_non_empty(self, node, c) -> T.Array:
        """
        With only one type and a "+" / "*" suffix, it's an homogeneous list.
        In this case, if there is a "only" qualifier it is ignored.
        With more than one type and a "+" / "*" suffix, it's a tuple type
        with extra items type. Here too, any "only" qualifier will be ignored.
        Without a suffix, it's a tuple type, the "only" qualifier is enforced.
        """
        _, array_prefix, first_item, other_items, extra, _, card = self.unspace(c)

        items = self.gather_separated_list(first_item, other_items)

        if extra is None:  # No suffix -> tuple typing
            additional_items = "only" not in array_prefix
        elif extra == "+":
            additional_items = items[-1]
            # Don't remove it from required items, there must be at least one
        else:  # Last type is the type of extra items
            additional_items = items[-1]
            items = items[:-1]
        if card[0] is not None and len(types) >= card[0]:
            card = (None, card[1])  # Constraint is redundant
        if card[1] is not None and not additional_items and len(types) < card[1]:
            raise ValueError(
                f"An array cannot be both {len(types)} and <={card[1]} items long"
            )

        return T.Array(items=items, additional_items=additional_items, cardinal=card,
                       unique="unique" in array_prefix)

    def visit_array_prefix(self, node, c) -> Set[str]:
        """Return a set of strings among "unique" and "only"."""
        r = set()
        for word in ("unique", "only"):
            if word in node.text:
                r.add(word)
        return r

    def visit_array_extra(self, node, c) -> str:
        # This rule is space-free
        if len(c) == 0:
            return None
        else:
            return node.children[0].text

    def visit_opt_definitions(self, node, c) -> T.Definitions:
        if len(c) == 0:  # Empty definition
            return T.Definitions(values={})
        else:
            _, defs = self.unspace(c[0])
            return defs

    def visit_definitions(self, node, c) -> T.Definitions:
        first_def, other_defs_with_and = self.unspace(c)
        other_defs = [d[1] for d in other_defs_with_and]
        items = (first_def, *other_defs)
        return T.Definitions(values=dict(items))

    def visit_definition(self, node, c) -> Tuple[str, T.Type]:
        id, _, type = self.unspace(c)
        return (id, type)

    def visit_def_identifier(self, node, c) -> str:
        return node.text

    def visit_def_reference(self, node, c) -> T.Reference:
        return T.Reference(value=c[1])

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

