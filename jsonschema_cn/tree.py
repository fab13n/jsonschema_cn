from abc import ABC, abstractmethod
from typing import NamedTuple, Optional, Set
import json
import jsonschema


class Type(ABC):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    @abstractmethod
    def to_jsonschema(self):
        pass

    def __str__(self):
        a = [str(arg) for arg in self.args] + [
            k + "=" + str(v) for k, v in self.kwargs.items()
        ]
        return f"{self.__class__.__name__}({', '.join(a)})"

    __repr__ = __str__


class Schema(Type):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._jsonschema = None

    def to_jsonschema(self, check_definitions=True):
        r = self.args[0].to_jsonschema()
        definitions = self.args[1].args[0]
        if definitions:
            r["definitions"] = {k: v.to_jsonschema() for k, v in definitions.items()}
        if check_definitions:
            for k in self.get_references(r):
                if k not in definitions.keys():
                    raise ValueError(f"Missing definition for {k}")
        r["$schema"] = "http://json-schema.org/draft-07/schema#"
        return r

    def get_references(self, x) -> Set[str]:
        """Extract every definition usage from a schema, so that it can be checked
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
            for schema in (self, other):
                content = schema.args[0]
                if isinstance(content, Operator) and content.args[0] == op:
                    args.extend(content.args[1:])
                else:
                    args.append(it)
            combined_content = Operator(op, *args)
            combined_defs = self.args[1] | other.args[1]
            return Schema(combined_content, combined_defs)
        elif op == 'anyOf' and isinstance(other, Definitions):
            combined_defs = self.args[1] | other
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

    def to_jsonschema(self):
        return {k: v.to_jsonschema() for k, v in self.args[0].items()}

    def __or__(self, other):
        if isinstance(other, Definitions):
            overlap = set(self.args[0].keys()) & set(other.args[0].keys())
            if overlap:
                conflicts = ", ".join(sorted(overlap))
                raise ValueError("Cannot merge definitions, conflict over {conflicts}")
            defs = dict(self.args[0])
            defs.update(other.args[0])
            return Definitions(defs)
        elif isinstance(other, Schema):
            return other | self
        else:
            raise ValueError("Cannot perform 'or' on Definitions and that")


class Integer(Type):
    def to_jsonschema(self):
        (card_min, card_max) = self.kwargs["cardinal"]
        mult = self.kwargs["multiple"]
        r = {"type": "integer"}
        if card_min is not None:
            r["minimum"] = card_min
        if card_max is not None:
            r["maximum"] = card_max
        if mult is not None:
            r["multipleOf"] = mult
        return r


class String(Type):
    def to_jsonschema(self):
        card = self.kwargs.get("cardinal", (None, None))
        r = {"type": "string"}
        if card is None:
            return r
        if isinstance(card, int):
            card = (card, card)
        card_min, card_max = card
        if card_min is not None:
            r["minLength"] = card_min
        if card_max is not None:
            r["maxLength"] = card_max
        if "format" in self.kwargs:
            r["format"] = self.kwargs["format"]
        if "regex" in self.kwargs:
            r["pattern"] = self.kwargs["regex"]
        return r


class Litteral(Type):
    def to_jsonschema(self):
        return {"type": self.args[0]}


class Constant(Type):
    def to_jsonschema(self):
        return {"const": self.args[0]}


class Operator(Type):
    def to_jsonschema(self):
        op = self.args[0]
        args = self.args[1:]
        return {op: [a.to_jsonschema() for a in args]}


class Not(Type):
    def __not__(self):
        return self.args[0]
    def to_jsonschema(self):
        return {"not": self.args[0].to_jsonschema()}


class Enum(Type):
    def to_jsonschema(self):
        return {"enum": list(self.args)}


class ObjectProperty(NamedTuple):
    name: Optional[str]
    optional: bool
    type: Type


class Object(Type):
    def to_jsonschema(self):
        # TODO: detect inconsistency between "only" and a "_" property wildcard
        pairs = self.kwargs.get("properties", {})
        card_min, card_max = self.kwargs.get("cardinal", (None, None))
        r = {"type": "object"}
        properties = {}
        required = []
        for (k, opt, v) in pairs:
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
        if (
            not self.kwargs.get("additional_properties")
            and "additionalProperties" not in r
        ):
            r["additionalProperties"] = False

        implicit_card_min = len(required)
        implicit_card_max = (
            len(properties) if r.get("additionalProperties") is False else None
        )

        if 'property_names' in self.kwargs:
            r['propertyNames'] = self.kwargs['property_names'].to_jsonschema()
            # TODO it would be neat to accept definitions here

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
    def to_jsonschema(self):
        types = self.kwargs["types"]
        extra_type = self.kwargs["additional_types"]
        card_min, card_max = self.kwargs["cardinal"]
        r = {"type": "array"}

        if types:  # Tuple array
            r["items"] = [t.to_jsonschema() for t in types]
            if extra_type is False:  # No extra items allowed
                r["additionalItems"] = False
            elif extra_type is True:  # Extra items with any type
                pass
            else:  # Forced type for extra items
                r["additionalItems"] = extra_type.to_jsonschema()
        elif isinstance(extra_type, Type):  # List array with homogeneous type
            r["items"] = extra_type.to_jsonschema()

        implicit_card_min = len(types)
        implicit_card_max = len(types) if extra_type is False else None

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

        if self.kwargs.get("unique"):
            r['uniqueItems'] = True

        return r


class Pointer(Type):
    def to_jsonschema(self):
        return {"$ref": "#/definitions/" + self.args[0]}
