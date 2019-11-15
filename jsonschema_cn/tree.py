from abc import ABC, abstractmethod
from typing import NamedTuple, Optional, Set, Tuple
import json
import jsonschema
import re
import logging


# Logger for Schema visitors
vlog = logging.getLogger("jsonschema_cn:visitor")


class Type(ABC):

    CONSTRUCTOR_KWARGS: Tuple[str, ...] = ()

    def __init__(self, **kwargs):
        self._jsonschema = None  # Will be filled as a cache on demand
        for name in self.CONSTRUCTOR_KWARGS:
            setattr(self, name, kwargs[name])

    @abstractmethod
    def to_jsonschema(self):
        pass

    @property
    def jsonschema(self):
        """Cached compilation of the corresponding jsonschema."""
        if self._jsonschema is None:
            self._jsonschema = self.to_jsonschema()
        return self._jsonschema

    def __str__(self):
        a = [k + "=" + str(getattr(self, k)) for k in self.CONSTRUCTOR_KWARGS]
        return f"{self.__class__.__name__}({', '.join(a)})"

    def prettily(self):
        """Return a unicode, pretty-printed representation of me."""

        def indent(text):
            return "\n".join(("    " + line) for line in text.splitlines())

        if not self.CONSTRUCTOR_KWARGS:
            return self.__class__.__name__
        else:
            acc = []
            for name in self.CONSTRUCTOR_KWARGS:
                value = getattr(self, name)
                # TODO go through lists and tuples
                r = value.prettily() if isinstance(value, Type) else repr(value)
                acc.append(f"{name} = {r}")
            return self.__class__.__name__ + "(\n" + indent("\n".join(acc)) + "\n)"

    __repr__ = __str__

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        for name in self.CONSTRUCTOR_KWARGS:
            if getattr(self, name) != getattr(other, name):
                return False
        return True

    def visit(self, visitor):
        x = self.visit_down(visitor)
        if x is self:
            return x.visit_up(visitor)
        else:
            return x

    def visit_down(self, visitor):
        vlog.debug("down %s", self)
        name = f"visit_{self.__class__.__name__}_down"
        method = getattr(visitor, name, None)
        if method is not None:
            vlog.debug("match down %s", name)
            r = method(self)
        else:
            r = None
        return r if r is not None else self

    def visit_up(self, visitor):
        vlog.debug("up %s", self)
        if visitor is None:
            return self
        else:
            names = [
                f"visit_{self.__class__.__name__}_up",
                f"visit_{self.__class__.__name__}",
                "visit",
            ]
            for name in names:
                method = getattr(visitor, name, None)
                if method is not None:
                    vlog.debug("match up %s", name)
                    return method(self)
            return self


class Schema(Type):

    CONSTRUCTOR_KWARGS = ("value", "definitions")

    def to_jsonschema(self, check_definitions=True, prune_definitions=True):
        r = self.value.jsonschema
        if isinstance(r, dict):  # Could also be `False`
            if self.definitions.values:
                r["definitions"] = self.definitions.jsonschema
                if prune_definitions:
                    self._prune_definitions(r)
            if check_definitions:
                self._check_definitions(r)
            # Recreate the dict to change keys order
            r2 = {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "$comment": str(self),
            }
            r2.update(r)
            r = r2
        return r

    def _check_definitions(self, schema):
        """Verify that all references have their definition."""
        occurring_references = self._get_dict_references(schema)
        for k in occurring_references:
            if k not in self.definitions.values.keys():
                raise ValueError(f"Missing definition for {k}")

    def _prune_definitions(self, schema):
        """Remove unused definitions. May iterate more than once, because
        some references may be used in other definitions."""
        occurring_references = self._get_dict_references(schema)
        eliminated_references = False
        while True:
            for k in list(schema["definitions"].keys()):
                # Freeze the keys into a list, so that `del` won't interfere
                if k not in occurring_references:
                    del schema["definitions"][k]
                    eliminated_references = True
            if eliminated_references:
                # Some unused references have been removed.
                # By removing their definitions, maybe some other
                # references became unused => try to prune again.
                occurring_references = self._get_dict_references(schema)
                eliminated_references = False
            else:
                # Reached a fix-point, nothing left to eliminate
                return

    def _get_dict_references(self, x) -> Set[str]:
        """Extract every definition usage from a compiled jsonschema,
        so that it can be checked that they are all defined."""
        if isinstance(x, dict):
            if "$ref" in x:
                # Don't return immediately, there may be definitions in a "$ref".
                r = {x["$ref"].rsplit("/", 1)[-1]}
            else:
                r = set()
            for k, v in x.items():
                if k != "$ref":
                    r |= self._get_dict_references(v)
            return r
        elif isinstance(x, list):
            return set.union(*(self._get_dict_references(y) for y in x))
        else:
            return set()

    def _combine(self, other, op):
        args = []
        if isinstance(other, Schema):
            # Two schemas: combine main entries and merge defition dicts
            for schema in (self, other):
                content = schema.value
                if isinstance(content, Operator) and content.operator == op:
                    args.extend(content.values)  # Flatten associative operations
                else:
                    args.append(content)
            combined_content = Operator(operator=op, values=args)
            combined_defs = self.definitions | other.definitions
            return Schema(value=combined_content, definitions=combined_defs)
        elif op == "anyOf" and (
            isinstance(other, Definitions) or isinstance(other, dict)
        ):
            # Schema + additional definitions
            # TODO Maybe '+' is a more appropriate operator than '|'?
            if isinstance(other, dict):
                other = Definitions.from_dict(other)
            combined_defs = self.definitions | other
            return Schema(value=self.value, definitions=combined_defs)
        else:
            raise ValueError(
                "Schemas can only be combined with each other or with definitions"
            )

    def __and__(self, other):
        return self._combine(other, "allOf")

    def __or__(self, other):
        return self._combine(other, "anyOf")

    def validate(self, data=None):
        if data is None:  # Validate the schema itself
            jsonschema.Draft7Validator.check_schema(self.jsonschema)
        else:  # Validate a piece of data against the schema
            jsonschema.validate(
                data, self.jsonschema, format_checker=jsonschema.draft7_format_checker,
            )

    def __str__(self):
        if self.definitions.values:
            return f"{self.value} {self.definitions}"
        else:
            return self.value.__str__()

    def __repr__(self):
        return f"Schema('{self}')"

    def visit(self, visitor):
        s = super().visit_down(visitor)
        if s is not self:
            return s
        v = self.value.visit(visitor)
        d = self.definitions.visit(visitor)
        if v is self.value and d is self.definitions:
            s = self
        else:
            s = self.__class__(value=v, definitions=d)
        return s.visit_up(visitor)


class Definitions(Type):

    CONSTRUCTOR_KWARGS = ("values",)

    def to_jsonschema(self):
        return {k: v.jsonschema for k, v in self.values.items()}

    def __or__(self, other):
        if isinstance(other, Definitions) or isinstance(other, dict):
            if isinstance(other, dict):
                other = Definitions.from_dict(other)
            overlap = set(self.values.keys()) & set(other.values.keys())
            conflicts = sorted(
                name for name in overlap if self.values[name] != other.values[name]
            )
            if conflicts:
                raise ValueError(
                    f"Cannot merge definitions, conflict over {', '.join(conflicts)}"
                )
            defs = dict(self.values)
            defs.update(other.values)
            return Definitions(values=defs)
        elif isinstance(other, Schema):
            return other | self
        else:
            raise ValueError("Cannot perform 'or' on Definitions and that")

    @staticmethod
    def from_dict(d):
        definitions = Definitions(values={})
        for name, schema in d.items():
            if isinstance(schema, str):  # Convert src strings -> Schema
                from .peg_visitor import parse

                schema = parse("schema", schema)
            definitions |= schema.definitions
            definitions |= Definitions(values={name: schema.value})
        return definitions

    def __str__(self):
        if self.values:
            return "where " + " and ".join(f"{k} = {v}" for k, v in self.values.items())
        else:
            return "<empty definitions>"

    def visit(self, visitor):
        s = super().visit_down(visitor)
        if s is not self:
            return s
        visited = {name: type.visit(visitor) for name, type in self.values.items()}
        if any(a is not b for a, b in zip(visited.values(), self.values.values())):
            s = self.__class__(values=visited)
        else:
            s = self
        return s.visit_up(visitor)


class Integer(Type):

    CONSTRUCTOR_KWARGS = ("cardinal", "multiple")

    def to_jsonschema(self):
        (card_min, card_max) = self.cardinal
        r = {"type": "integer"}
        if card_min is not None:
            r["minimum"] = card_min
        if card_max is not None:
            r["maximum"] = card_max
        if self.multiple is not None:
            r["multipleOf"] = self.multiple
        return r

    def __str__(self):
        r = "integer"
        (card_min, card_max) = self.cardinal
        if card_min is not None and card_max is not None:
            r += "{" + str(card_min) + ", " + str(card_max) + "}"
        elif card_min is not None:
            r += "{" + str(card_min) + ", _}"
        elif card_max is not None:
            r += "{_, " + str(card_max) + "}"
        if self.multiple is not None:
            r += f"/{self.multiple}"
        return r


class String(Type):

    CONSTRUCTOR_KWARGS = ("cardinal", "format", "regex")

    def to_jsonschema(self):
        r = {"type": "string"}
        card_min, card_max = self.cardinal
        if card_min is not None:
            r["minLength"] = card_min
        if card_max is not None:
            r["maxLength"] = card_max
        if self.format is not None:
            r["format"] = self.format
        if self.regex is not None:
            r["pattern"] = self.regex
        return r

    def __str__(self):
        if self.format is not None:
            r = f'f"{self.format}"'
        elif self.regex is not None:
            r = f'r"{self.regex}"'  # TODO What about escaping special chars?
        else:
            r = "string"
        (card_min, card_max) = self.cardinal
        if card_min is not None and card_max is not None:
            r += "{" + str(card_min) + ", " + str(card_max) + "}"
        elif card_min is not None:
            r += "{" + str(card_min) + ", _}"
        elif card_max is not None:
            r += "{_, " + str(card_max) + "}"
        return r


class Forbidden(Type):
    CONSTRUCTOR_KWARGS = ()

    def to_jsonschema(self):
        return False

    def __str__(self):
        return "forbidden"


class Litteral(Type):
    CONSTRUCTOR_KWARGS = ("value",)

    def to_jsonschema(self):
        return {"type": self.value}

    def __str__(self):
        return self.value


class Constant(Type):
    CONSTRUCTOR_KWARGS = ("value",)

    def to_jsonschema(self):
        return {"const": self.value}

    def __str__(self):
        return f"`{self.value}`"


class Operator(Type):
    CONSTRUCTOR_KWARGS = ("operator", "values")

    def to_jsonschema(self):
        return {self.operator: [v.jsonschema for v in self.values]}

    def __str__(self):
        op = {"anyOf": "|", "oneOf": "|", "allOf": "&"}[self.operator]
        return op.join(v.__str__() for v in self.values)

    def visit(self, visitor):
        s = self.visit_down(visitor)
        if s is not self:
            return s
        visited = [c.visit(visitor) for c in self.values()]
        if any(a is not b for a, b in zip(visited, self.values)):
            s = self.__class__(operator=self.operator, values=visited)
        else:
            s = self
        return s.visit_up(visitor)


class Not(Type):
    CONSTRUCTOR_KWARGS = ("value",)

    def to_jsonschema(self):
        return {"not": self.value.jsonschema}

    def __str__(self):
        return f"not {self.value}"

    def visit(self, visitor):
        s = self.visit_down(visitor)
        if s is not self:
            return s
        v = self.value.visit(visitor)
        if v is self.value:
            s = self
        else:
            s = self.__class__(value=v)
        return s.visit_up(visitor)


class Enum(Type):
    CONSTRUCTOR_KWARGS = ("values",)

    def to_jsonschema(self):
        return {"enum": list(self.values)}

    def __str__(self):
        return "|".join(f"`{json.dumps(v)}`" for v in self.values)


class Reference(Type):
    CONSTRUCTOR_KWARGS = ("value",)

    def to_jsonschema(self):
        return {"$ref": "#/definitions/" + self.value}

    def __str__(self):
        return f"<{self.value}>"


class ObjectProperty(NamedTuple):
    name: Optional[str]
    optional: bool
    type: Type


class Object(Type):

    CONSTRUCTOR_KWARGS = (
        "properties",
        "cardinal",
        "additional_property_types",
        "additional_property_names",
    )

    def to_jsonschema(self):
        card_min, card_max = self.cardinal
        r = {"type": "object"}
        properties = {}
        required = []
        for (k, opt, v) in self.properties:
            if not opt:
                required.append(k)
            properties[k] = v.jsonschema if v is not None else True
        if required:
            r["required"] = required
        if properties:
            r["properties"] = properties

        if self.additional_property_types is False:
            r["additionalProperties"] = False
        elif self.additional_property_types is not None:
            r["additionalProperties"] = self.additional_property_types.jsonschema
        if self.additional_property_names is not None:
            r["propertyNames"] = self.additional_property_names.jsonschema

        implicit_card_min = len(required)
        implicit_card_max = (
            len(properties) if r.get("additionalProperties") is False else None
        )
        if card_min is not None:
            if card_min > implicit_card_min:
                r["minProperties"] = card_min
            if implicit_card_max is not None and card_min > implicit_card_max:
                raise ValueError(
                    f"Can only have up to {implicit_card_max} properties, not {card_min}"
                )
        if card_max is not None:
            if implicit_card_max is None or card_max < implicit_card_max:
                r["maxProperties"] = card_max
            if implicit_card_min > card_max:
                raise ValueError(
                    f"Must have at least {implicit_card_min} properties, which is more than {card_max}"
                )
        return r

    def __str__(self):
        if self.additional_property_names and self.additional_property_types:
            only = f"only {self.additional_property_names}: {self.additional_property_types}"
        elif self.additional_property_names:
            only = f"only {self.additional_property_names}"
        elif self.additional_property_types is True:
            only = f"only _: {self.additional_property_types}"
        elif self.additional_property_types is False:
            only = f"only"
        else:
            only = None
        if self.properties:

            def needs_quotes(name):
                return name in ("only", "unique") or not re.match(r"^\w+$", name)

            def pair_str(item):
                (name, opt, t) = item
                opt = "?" if opt else ""
                if needs_quotes(name):
                    name = json.dumps(name)
                t = "_" if t is None else t.__str__()
                return f"{name}{opt}: {t}"

            properties = ", ".join(pair_str(item) for item in self.properties)
        else:
            properties = None

        if only == "only":
            r = "only " + properties if properties else "only"
        elif only is None:
            r = properties or ""
        elif properties is not None:
            r = only + ", " + properties
        else:
            r = only
        r = "{" + r + "}"
        (card_min, card_max) = self.cardinal
        if card_min is not None and card_max is not None:
            r += "{" + str(card_min) + ", " + str(card_max) + "}"
        elif card_min is not None:
            r += "{" + str(card_min) + ", _}"
        elif card_max is not None:
            r += "{_, " + str(card_max) + "}"
        return r

    def visit(self, visitor):
        s = self.visit_down(visitor)
        if s is not self:
            return s
        visited_props = [
            ObjectProperty(p[0], p[1], p[2].visit(visitor)) for p in self.properties
        ]
        if isinstance(self.additional_property_types, Type):
            addprops = self.additional_properties.visit(visitor)
        else:
            addprops = self.additional_property_types

        if addprops is not self.additional_property_types or any(
            a[2] is not b[2] for a, b in zip(visited_props, self.properties)
        ):
            s = self.__class__(
                properties=visited_props,
                additional_property_types=addprops,
                additional_property_names=self.additional_property_names,
                cardinal=self.cardinal,
            )
        else:
            s = self
        return s.visit_up(visitor)


class Array(Type):

    CONSTRUCTOR_KWARGS = ("items", "additional_items", "cardinal", "unique")

    def to_jsonschema(self):
        # types = self.kwargs["types"]
        # extra_type = self.kwargs["additional_types"]
        # card_min, card_max = self.kwargs["cardinal"]
        r = {"type": "array"}

        if self.items:  # Tuple array
            r["items"] = [item.jsonschema for item in self.items]
            if self.additional_items is False:  # No extra items allowed
                r["additionalItems"] = False
            elif self.additional_items is True:  # Extra items with any type
                pass
            else:  # extra items allowed, but wiht a constrained type
                r["additionalItems"] = self.additional_items.jsonschema
        elif isinstance(
            self.additional_items, Type
        ):  # List array with homogeneous type
            r["items"] = self.additional_items.jsonschema

        card_min, card_max = self.cardinal
        implicit_card_min = len(self.items)
        implicit_card_max = len(self.items) if self.additional_items is False else None
        if card_min is not None and card_min > implicit_card_min:
            r["minItems"] = card_min
            if implicit_card_max is not None and card_min > implicit_card_max:
                raise ValueError(
                    f"Can only have up to {implicit_card_max} items, not {card_min}"
                )
        if card_max is not None:
            if implicit_card_min > card_max:
                raise ValueError(
                    f"Must have at least {implicit_card_min} items, which is more than {card_max}"
                )
            if implicit_card_max is None or card_max < implicit_card_max:
                r["maxItems"] = card_max

        if self.unique:
            r["uniqueItems"] = True

        return r

    def __str__(self):
        if self.additional_items is False:
            prefix = f"only "
        else:
            prefix = ""
        if self.unique:
            prefix += "unique "
        items = [str(item) for item in self.items]
        if isinstance(self.additional_items, Type):
            items.append(f"{self.additional_items}*")
        items = ", ".join(items)
        r = f"[{prefix}{items}]"
        if prefix and items:
            r = f"[{prefix}{items}]"
        elif prefix:
            r = f"[{prefix.strip()}]"
        elif items:
            r = f"[{items}]"
        else:
            r = "[ ]"
        (card_min, card_max) = self.cardinal
        if card_min is not None and card_max is not None:
            r += "{" + str(card_min) + ", " + str(card_max) + "}"
        elif card_min is not None:
            r += "{" + str(card_min) + ", _}"
        elif card_max is not None:
            r += "{_, " + str(card_max) + "}"
        return r

    def visit(self, visitor):
        s = self.visit_down(visitor)
        if s is not self:
            return s
        visited_items = [c.visit(visitor) for c in self.items]
        if isinstance(self.additional_items, Type):
            additems = self.additional_items.visit(visitor)
        else:
            additems = self.additional_items
        if additems is not self.additional_items or any(
            a is not b for a, b in zip(visited_items, self.items)
        ):
            s = self.__class__(
                items=visited_items,
                additional_items=additems,
                unique=self.unique,
                cardinal=self.cardinal,
            )
        else:
            s = self
        return s.visit_up(visitor)


class Conditional(Type):

    CONSTRUCTOR_KWARGS = ("if_term", "then_term", "else_term")

    def to_jsonschema(self):
        r = {"if": self.if_term.jsonschema, "then": self.then_term.jsonschema}
        if self.else_term:
            r["else"] = self.else_term.jsonschema
        return r

    def __str__(self):
        r = f"if {self.if_term} then {self.then_term}"
        if self.else_term is not None:
            r += f" {self.else_term}"
        return r

    def visit(self, visitor):
        s = self.visit_down(visitor)
        if s is not self:
            return s
        if_t = self.if_term.visit(visitor)
        then_t = self.then_term.visit(visitor)
        if self.else_term is not None:
            else_t = self.else_term.visit(visitor)
        else:
            else_t = None
        if (
            if_t is not self.if_term
            or then_t is not self.then_term
            or else_t is not self.else_term
        ):
            s = self.__class__(if_term=if_t, then_term=then_t, else_term=else_t)
        else:
            s = self
        return s.visit_up(visitor)
