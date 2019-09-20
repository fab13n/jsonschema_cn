from abc import ABC, abstractmethod
from typing import NamedTuple, Optional
import json


class Type(ABC):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    @abstractmethod
    def to_schema(self):
        pass

    def to_json(self):
        return json.dumps(self.to_schema())

    def __str__(self):
        a = [str(arg) for arg in self.args] + [
            k + "=" + str(v) for k, v in self.kwargs.items()
        ]
        return f"{self.__class__.__name__}({', '.join(a)})"

    __repr__ = __str__


class Entry(Type):
    def to_schema(self):
        r = self.args[0].to_schema()
        definitions = self.kwargs.get("definitions")
        if definitions:
            r["definitions"] = {k: v.to_schema() for k, v in definitions.items()}
        r["$schema"] = "http://json-schema.org/draft-07/schema#"
        return r


class Integer(Type):
    def to_schema(self):
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
    def to_schema(self):
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
    def to_schema(self):
        return {"type": self.args[0]}


class Constant(Type):
    def to_schema(self):
        return {"const": self.args[0]}


class Operator(Type):
    def to_schema(self):
        op = self.args[0]
        args = self.args[1:]
        return {op: [a.to_schema() for a in args]}


class Enum(Type):
    def to_schema(self):
        return {"enum": list(self.args)}


class ObjectProperty(NamedTuple):
    name: Optional[str]
    optional: bool
    type: Type


class Object(Type):
    def to_schema(self):
        pairs = self.kwargs.get("properties", {})
        card_min, card_max = self.kwargs.get("cardinal", (None, None))
        r = {"type": "object"}
        properties = {}
        required = []
        for (k, opt, v) in pairs:
            if k is None:
                r["additionalProperties"] = v.to_schema()
                continue
            if not opt:
                required.append(k)
            if v is not None:
                properties[k] = v.to_schema()
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
    def to_schema(self):
        types = self.kwargs["types"]
        extra_type = self.kwargs["additional_types"]
        card_min, card_max = self.kwargs["cardinal"]
        r = {"type": "array"}

        if types:  # Tuple array
            r["items"] = [t.to_schema() for t in types]
            if extra_type is False:  # No extra items allowed
                r["additionalItems"] = False
            elif extra_type is True:  # Extra items with any type
                pass
            else:  # Forced type for extra items
                r["additionalItems"] = extra_type.to_schema()
        elif isinstance(extra_type, Type):  # List array with homogeneous type
            r["items"] = extra_type.to_schema()

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

        return r
