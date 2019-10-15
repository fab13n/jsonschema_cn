from abc import ABC, abstractmethod
from typing import NamedTuple, Optional, Set, Tuple
import json
import jsonschema


class Type(ABC):

    KWARG_NAMES: Tuple[str, ...] = ()

    def __init__(self, **kwargs):
        for name in self.KWARG_NAMES:
            setattr(self, name, kwargs[name])

    @abstractmethod
    def to_jsonschema(self):
        pass

    def __str__(self):
        a = [k + "=" + str(getattr(self, k)) for k in self.KWARG_NAMES]
        return f"{self.__class__.__name__}({', '.join(a)})"

    __repr__ = __str__


class Schema(Type):

    KWARG_NAMES = ("value", "definitions")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._jsonschema = None  # Will be filled as a cache on demand

    def to_jsonschema(self, check_definitions=True):
        r = self.value.to_jsonschema()
        definitions = self.definitions.values
        if definitions:
            r["definitions"] = {k: v.to_jsonschema() for k, v in definitions.items()}
        if check_definitions:
            for k in self.get_references(r):
                if k not in definitions.keys():
                    raise ValueError(f"Missing definition for {k}")
        r["$schema"] = "http://json-schema.org/draft-07/schema#"
        return r

    def get_references(self, x) -> Set[str]:
        """Extract every definition usage from a jsonschema, so that it can be checked
        that they are all defined."""
        if isinstance(x, dict):
            if "$ref" in x:
                return {x["$ref"].rsplit("/", 1)[-1]}
            else:
                return set.union(*(self.get_references(y) for y in x.values()))
        elif isinstance(x, list):
            return set.union(*(self.get_references(y) for y in x))
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
        elif op == 'anyOf' and isinstance(other, Definitions):
            # Schema + additional definitions
            # TODO Maybe '+' is a more appropriate operator than '|'?
            combined_defs = self.defitions | other
            return Schema(self.args[0], combined_defs)
        else:
            raise ValueError("Schemas can only be combined with each other")

    def __and__(self, other):
        return self._combine(other, 'allOf')

    def __or__(self, other):
        return self._combine(other, 'anyOf')

    @property
    def jsonschema(self):
        """Cached compilation of the corresponding jsonschema."""
        if self._jsonschema is None:
            self._jsonschema = self.to_jsonschema()
        return self._jsonschema

    def validate(self, data):
        jsonschema.validate(
            data,
            self.jsonschema,
            format_checker=jsonschema.draft7_format_checker,
        )


class Definitions(Type):

    KWARG_NAMES = ("values",)

    def to_jsonschema(self):
        return {k: v.to_jsonschema() for k, v in self.values.items()}

    def __or__(self, other):
        if isinstance(other, Definitions):
            overlap = set(self.values.keys()) & set(other.values.keys())
            if overlap:
                conflicts = ", ".join(sorted(overlap))
                raise ValueError("Cannot merge definitions, conflict over {conflicts}")
            defs = dict(self.values)
            defs.update(other.values)
            return Definitions(defs)
        elif isinstance(other, Schema):
            return other | self
        else:
            raise ValueError("Cannot perform 'or' on Definitions and that")


class Integer(Type):

    KWARG_NAMES = ("cardinal", "multiple")

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

    KWARG_NAMES = ("cardinal", "format", "regex")

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


class Litteral(Type):
    KWARG_NAMES = ("value",)
    def to_jsonschema(self):
        return {"type": self.value}


class Constant(Type):
    KWARG_NAMES = ("value",)
    def to_jsonschema(self):
        return {"const": self.value}


class Operator(Type):
    KWARG_NAMES = ("operator", "values")
    def to_jsonschema(self):
        return {self.operator: [v.to_jsonschema() for v in self.values]}


class Not(Type):
    KWARG_NAMES = ("value",)
    def to_jsonschema(self):
        return {"not": self.value.to_jsonschema()}


class Enum(Type):
    KWARG_NAMES = ("values",)
    def to_jsonschema(self):
        return {"enum": list(self.values)}


class ObjectProperty(NamedTuple):
    name: Optional[str]
    optional: bool
    type: Type


class Object(Type):

    KWARG_NAMES = ("properties", "cardinal", "additional_properties", "property_names")

    def to_jsonschema(self):
        # TODO: detect inconsistency between "only" and a "_" property wildcard
        card_min, card_max = self.cardinal
        r = {"type": "object"}
        properties = {}
        required = []
        for (k, opt, v) in self.properties:
            if k is None:
                r["additionalProperties"] = v.to_jsonschema()
                continue
            if not opt:
                required.append(k)
            if v is not None:
                properties[k] = v.to_jsonschema()
        if required:
            r["required"] = required
        if properties:
            r["properties"] = properties
        if not self.additional_properties and "additionalProperties" not in r:
            r["additionalProperties"] = False

        if self.property_names is not None:
            r['propertyNames'] = self.property_names.to_jsonschema()
            # TODO it would be neat to accept definitions here

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

    KWARG_NAMES = ("items", "additional_items", "cardinal", "unique")

    def to_jsonschema(self):
        #types = self.kwargs["types"]
        #extra_type = self.kwargs["additional_types"]
        #card_min, card_max = self.kwargs["cardinal"]
        r = {"type": "array"}

        if self.items:  # Tuple array
            r["items"] = [item.to_jsonschema() for item in self.items]
            if self.additional_items is False:  # No extra items allowed
                r["additionalItems"] = False
            elif self.additional_items is True:  # Extra items with any type
                pass
            else:  # extra items allowed, but wiht a constrained type
                r["additionalItems"] = self.additional_items.to_jsonschema()
        elif isinstance(self.additional_items, Type):  # List array with homogeneous type
            r["items"] = self.additional_items.to_jsonschema()

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


class Reference(Type):
    KWARG_NAMES = ("value",)
    def to_jsonschema(self):
        return {"$ref": "#/definitions/" + self.value}
