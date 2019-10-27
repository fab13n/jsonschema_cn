from abc import ABC, abstractmethod
from typing import NamedTuple, Optional, Set, Tuple
import json
import jsonschema


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
            return '\n'.join(('    ' + line) for line in text.splitlines())
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


class Schema(Type):

    CONSTRUCTOR_KWARGS = ("value", "definitions")

    def to_jsonschema(self, check_definitions=True, prune_definitions=True):
        r = self.value.jsonschema
        if isinstance(r, dict):  # Could also be `False`
            if self.definitions.values:
                r['definitions'] = self.definitions.jsonschema
                if prune_definitions:
                    self._prune_definitions(r)
            if check_definitions:
                self._check_definitions(r)
            r["$schema"] = "http://json-schema.org/draft-07/schema#"
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
            for k in list(schema['definitions'].keys()):
                # Freeze the keys into a list, so that `del` won't interfere
                if k not in occurring_references:
                    del schema['definitions'][k]
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
        elif op == 'anyOf' and (isinstance(other, Definitions) or isinstance(other, dict)):
            # Schema + additional definitions
            # TODO Maybe '+' is a more appropriate operator than '|'?
            if isinstance(other, dict):
                other = Definitions.from_dict(other)
            combined_defs = self.definitions | other
            return Schema(value=self.value, definitions=combined_defs)
        else:
            raise ValueError("Schemas can only be combined with each other or with definitions")


    def __and__(self, other):
        return self._combine(other, 'allOf')

    def __or__(self, other):
        return self._combine(other, 'anyOf')

    def validate(self, data=None):
        if data is None:  # Validate the schema itself
            jsonschema.Draft7Validator.check_schema(self.jsonschema)
        else:  # Validate a piece of data against the schema
            jsonschema.validate(
                data,
                self.jsonschema,
                format_checker=jsonschema.draft7_format_checker,
            )


class Definitions(Type):

    CONSTRUCTOR_KWARGS = ("values",)

    def to_jsonschema(self):
        return {k: v.jsonschema for k, v in self.values.items()}

    def __or__(self, other):
        if isinstance(other, Definitions) or isinstance(other, dict):
            if isinstance(other, dict):
                other = Definitions.from_dict(other)
            overlap = set(self.values.keys()) & set(other.values.keys())
            conflicts = sorted(name for name in overlap if self.values[name] != other.values[name])
            if conflicts:
                raise ValueError(f"Cannot merge definitions, conflict over {', '.join(conflicts)}")
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
            if isinstance(schema, str):
                from .visitor import parse
                schema = parse('schema', schema)
            definitions |= schema.definitions
            definitions |= Definitions(values={name: schema.value})
        return definitions


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


class Forbidden(Type):
    CONSTRUCTOR_KWARGS = ()
    def to_jsonschema(self):
        return False


class Litteral(Type):
    CONSTRUCTOR_KWARGS = ("value",)
    def to_jsonschema(self):
        return {"type": self.value}


class Constant(Type):
    CONSTRUCTOR_KWARGS = ("value",)
    def to_jsonschema(self):
        return {"const": self.value}


class Operator(Type):
    CONSTRUCTOR_KWARGS = ("operator", "values")
    def to_jsonschema(self):
        return {self.operator: [v.jsonschema for v in self.values]}


class Not(Type):
    CONSTRUCTOR_KWARGS = ("value",)
    def to_jsonschema(self):
        return {"not": self.value.jsonschema}


class Enum(Type):
    CONSTRUCTOR_KWARGS = ("values",)
    def to_jsonschema(self):
        return {"enum": list(self.values)}


class Reference(Type):
    CONSTRUCTOR_KWARGS = ("value",)
    def to_jsonschema(self):
        return {"$ref": "#/definitions/" + self.value}


class ObjectProperty(NamedTuple):
    name: Optional[str]
    optional: bool
    type: Type


class Object(Type):

    CONSTRUCTOR_KWARGS = ("properties", "cardinal",
                          "additional_property_types",
                          "additional_property_names")

    def to_jsonschema(self):
        card_min, card_max = self.cardinal
        r = {"type": "object"}
        properties = {}
        required = []
        for (k, opt, v) in self.properties:
            if not opt:
                required.append(k)
            if v is not None:
                properties[k] = v.jsonschema
        if required:
            r["required"] = required
        if properties:
            r["properties"] = properties

        if self.additional_property_types is False:
            r["additionalProperties"] = False
        elif self.additional_property_types is not None:
            r["additionalProperties"] = self.additional_property_types.jsonschema
        if self.additional_property_names is not None:
            r['propertyNames'] = self.additional_property_names.jsonschema

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


class Array(Type):

    CONSTRUCTOR_KWARGS = ("items", "additional_items", "cardinal", "unique")

    def to_jsonschema(self):
        #types = self.kwargs["types"]
        #extra_type = self.kwargs["additional_types"]
        #card_min, card_max = self.kwargs["cardinal"]
        r = {"type": "array"}

        if self.items:  # Tuple array
            r["items"] = [item.jsonschema for item in self.items]
            if self.additional_items is False:  # No extra items allowed
                r["additionalItems"] = False
            elif self.additional_items is True:  # Extra items with any type
                pass
            else:  # extra items allowed, but wiht a constrained type
                r["additionalItems"] = self.additional_items.jsonschema
        elif isinstance(self.additional_items, Type):  # List array with homogeneous type
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
            r['uniqueItems'] = True

        return r

class Conditional(Type):

    CONSTRUCTOR_KWARGS = ("if_term", "then_term", "else_term")

    def to_jsonschema(self):
        r = {"if": self.if_term.jsonschema, "then": self.then_term.jsonschema}
        if self.else_term:
            r["else"] = self.else_term.jsonschema
        return r
