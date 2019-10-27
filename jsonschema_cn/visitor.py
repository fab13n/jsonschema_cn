from parsimonious import NodeVisitor
from collections import Sequence
from typing import Tuple, Optional, Set, Dict
import json

from . import tree as T
from .grammar import grammar
from .unspace import UnspaceVisitor


class TreeBuildingVisitor(NodeVisitor):

    SHELL_EXPRESSIONS = {
        "simple_type": 0,
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

    @staticmethod
    def unescape_string(escaped):
        return escaped.encode("utf-8").decode("unicode_escape")

    @staticmethod
    def gather_separated_list(first_item, other_items_with_separators) -> tuple:
        return (first_item, ) + tuple(item[1] for item in other_items_with_separators)

    def visit_schema(self, node, c) -> T.Schema:
        value, definitions = c
        return T.Schema(value=value, definitions=definitions)

    def visit_sequence_and(self, node, c) -> T.Type:
        first, rest = c
        if len(rest):
            values = self.gather_separated_list(first, rest)
            return T.Operator(operator="allOf", values=values)
        else:
            return first

    def visit_type(self, node, c) -> T.Type:
        first, rest = c
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
        return T.Not(value=c[1])

    def visit_string(self, node, c) -> T.String:
        return T.String(cardinal=c[1], format=None, regex=None)

    def visit_integer(self, node, c) -> T.Integer:
        _, cardinal, multiple = c
        return T.Integer(cardinal=cardinal, multiple=multiple)

    def visit_litteral(self, node, c) -> T.Litteral:
        # This rule is space-free
        return T.Litteral(value=node.children[0].text.lower())

    def visit_kw_forbidden(self, node, c) -> T.Forbidden:
        return T.Forbidden()

    def visit_lit_string(self, node, c) -> str:
        # This rule is space-free
        return node.text[1:-1]

    def visit_lit_regex(self, node, c) -> T.String:
        # This rule is space-free
        # Don't unescape the string
        return T.String(format=None, cardinal=(None, None), regex=node.children[-1].text[1:-1])

    def visit_lit_format(self, node, c) -> T.String:
        # This rule is space-free
        # No need to unescape
        return T.String(cardinal=(None, None), regex=None, format=node.children[-1].text[1:-1])

    def visit_opt_multiple(self, node, c) -> Optional[int]:
        return None if len(c) == 0 else c[0][1]

    def visit_opt_cardinal(self, node, c) -> Tuple[Optional[int], Optional[int]]:
        # generic_visit didn't detect card_1, probably due to some node optimization?
        if len(c) == 0:  # Empty cardinal
            return (None, None)
        uc = c[0][1]
        if isinstance(uc, int):
            return (uc, uc)
        else: # Pair of ints/nulls
            return uc

    def visit_card_min(self, node, c) -> Tuple[int, None]:
        return (c[0], None)

    def visit_card_max(self, node, c) -> Tuple[None, int]:
        return (None, c[2])

    def visit_lit_integer(self, node, c) -> int:
        # This rule is space-free
        text = node.text
        base = 16 if len(text) > 2 and text[1] == "x" else 10
        return int(text, base)

    def visit_constant(self, node, c) -> T.Constant:
        # This rule is space-free
        source = node.text  # No need to unescape
        if source[0] == '`':
            assert source[-1] == '`'
            source = source[1:-1]
        try:
            value = json.loads(source)
            return T.Constant(value=value)
        except json.JSONDecodeError:
            raise ValueError(f"{source} is not a valid JSON fragment")

    def visit_object_keyword(self, node, c) -> T.Object:
        return T.Object(
            properties=[],
            additional_property_types=None,
            additional_property_names=None,
            cardinal=c[-1])

    def visit_object_empty(self, node, c) -> T.Object:
        kwargs = {'properties': []}
        _,  additional_props, _, kwargs['cardinal'] = c
        kwargs.update(additional_props)
        return T.Object(**kwargs)

    def visit_object_non_empty(self, node, c) -> T.Object:
        kwargs = {}
        _,  additional_props, first_field, other_fields, _, kwargs['cardinal'] = c
        kwargs['properties'] = self.gather_separated_list(first_field, other_fields)
        kwargs.update(additional_props)
        return T.Object(**kwargs)

    def visit_object_pair(self, node, c) -> T.ObjectProperty:
        key, question, _, val = c
        if not isinstance(val, T.Type):  # wildcard
            val = None
        is_optional = bool(question) | isinstance(val, T.Forbidden)
        return T.ObjectProperty(self.unescape_string(key), is_optional, val)

    def visit_object_pair_unquoted_name(self, node, c) -> str:
        return node.text

    def visit_object_only(self, node, c) -> Tuple[bool, Optional[T.Type], Optional[T.Type]]:
        """Parse `only`, `only <pattern>`, `only <pattern>: <type>` + optional coma."""
        if len(c) == 0:  # Empty sequence
            return {'additional_property_names': None,
                    'additional_property_types': None}
        _, maybe_something, _ = c[0]
        if len(maybe_something) == 0: # keyword "only" alone
            return {'additional_property_names': None,
                    'additional_property_types': False}
        maybe_name, maybe_type = maybe_something[0]
        if len(maybe_name) == 0:
            maybe_name = None
        else:
            maybe_name = maybe_name[0]
        if len(maybe_type):
            maybe_type = maybe_type[0][1]
        else:
            maybe_type = None
        return {'additional_property_names': maybe_name,
                'additional_property_types': maybe_type}

    def visit_array_empty(self, node, c) -> T.Array:
        return T.Array(items=[], additional_items=True, cardinal=c[-1], unique=False)

    def visit_array_non_empty(self, node, c) -> T.Array:
        """
        With only one type and a "+" / "*" suffix, it's an homogeneous list.
        In this case, if there is a "only" qualifier it is ignored.
        With more than one type and a "+" / "*" suffix, it's a tuple type
        with extra items type. Here too, any "only" qualifier will be ignored.
        Without a suffix, it's a tuple type, the "only" qualifier is enforced.
        """
        _, array_prefix, first_item, other_items, extra, _, card = c

        items = self.gather_separated_list(first_item, other_items)

        if extra is None:  # No suffix -> tuple typing
            additional_items = "only" not in array_prefix
        elif extra == "+":
            additional_items = items[-1]
            # Don't remove it from required items, there must be at least one
        else:  # Last type is the type of extra items
            additional_items = items[-1]
            items = items[:-1]
        if card[0] is not None and len(items) >= card[0]:
            card = (None, card[1])  # Constraint is redundant
        if card[1] is not None and not additional_items and len(items) < card[1]:
            raise ValueError(
                f"An array cannot be both {len(items)} and <={card[1]} items long"
            )

        return T.Array(items=items, additional_items=additional_items, cardinal=card,
                       unique="unique" in array_prefix)

    def visit_array_prefix(self, node, c) -> Set[str]:
        """Return a set of strings among "unique" and "only"."""
        r = set()
        for word in ("unique", "only"):
            if word in node.text.lower():
                r.add(word)
        return r

    def visit_array_extra(self, node, c) -> str:
        # This rule is space-free
        if len(c) == 0:
            return None
        else:
            return node.children[0].text

    def visit_conditional(self, node, c):
        _, if_term, _, then_term, elif_parts, else_part = c
        else_term = else_part[0][1] if len(else_part) else None
        elif_terms = [[cond, val] for (_, cond, _, val) in elif_parts]

        def rec(c, t, elifs, e):
            """Change elif pairs into nested if/then/else."""
            if elifs:
                (c2, t2) = elifs[-1]
                return rec(c, t, elifs[:-1], rec(c2, t2, [], e))
            else:
                return T.Conditional(if_term=c, then_term=t, else_term= e)

        return rec(if_term, then_term, elif_terms, else_term)

    def visit_opt_definitions(self, node, c) -> T.Definitions:
        if len(c) == 0:  # Empty definition
            return T.Definitions(values={})
        else:
            _, defs = c[0]
            return defs

    def visit_definitions(self, node, c) -> T.Definitions:
        first_def, other_defs_with_and = c
        other_defs = [d[1] for d in other_defs_with_and]
        items = (first_def, *other_defs)
        return T.Definitions(values=dict(items))

    def visit_definition(self, node, c) -> Tuple[str, T.Type]:
        _, id, _, _, type = c
        return (id, type)

    def visit_def_identifier(self, node, c) -> str:
        return node.text

    def visit_def_reference(self, node, c) -> T.Reference:
        return T.Reference(value=c[1])

    def generic_visit(self, node, c) -> tuple:
        """ The generic visit method. """
        n = self.SHELL_EXPRESSIONS.get(node.expr_name)
        if n is None:
            return c
        elif isinstance(n, Sequence):
            return tuple(c[i] for i in n)
        elif isinstance(n, int):
            return c[n]
        else:
            raise ValueError(f"bad SHELL_EXPRESSIONS for {node.expr_name}")


jscn_visitor = TreeBuildingVisitor()
unspace_visitor = UnspaceVisitor()


def parse(what: str, source: str, verbose=False) -> T.Type:
    raw_tree = grammar[what].parse(source)
    unspaced_tree = unspace_visitor.visit(raw_tree)
    if verbose:
        print("PEG tree:\n" + unspaced_tree.prettily())
    parsed_tree = jscn_visitor.visit(unspaced_tree)
    if verbose:
        print("JSCN tree:\n" + parsed_tree.prettily())
    parsed_tree.source = source
    return parsed_tree
