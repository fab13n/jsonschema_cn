from collections import Sequence
from abc import ABC, abstractmethod
from numbers import Number

class Node(ABC):

    def __init__(self, *args):
        self.args = args

    @abstractmethod
    def tojson(self):
        pass

    def __str__(self):
        return f"{self.__class__.__name__}({', '.join(str(arg) for arg in self.args)})"

    __repr__ = __str__

    
class Integer(Node):
    # TODO handle optional constraints
    def tojson(self):
        (card_min, card_max), mult = self.args
        r = {"type": "integer"}
        if card_min is not None:
            r['minimum'] = card_min
        if card_max is not None:
            r['maximum'] = card_max
        if mult is not None:
            r["multipleOf"] = mult
        return r


class String(Node):
    def tojson(self):
        card = self.args[0]
        r = {"type": "string"}
        if card is None:
            return r
        if isinstance(card, int):
            card = (card, card)
        card_min, card_max = card
        if card_min is not None:
            r['minLength'] = card_min
        if card_max is not None:
            r['maxLength'] = card_max
        return r


class Litteral(Node):
    def tojson(self):
        return {"type": self.args[0]}


class Object(Node):
    def tojson(self):
        (pairs,) = self.args
        r = {}
        properties = {}
        required = []
        for (k, opt, v) in pairs:
            if k is None:
                r['additionalProperties'] = v.tojson()
                continue
            if not opt:
                required.append(k)
            if v is not None:
                properties[k] = v.tojson()
        if required:
            r['required'] = required
        if properties:
            r['properties'] = properties
        return r

class Array(Node):
    def tojson(self):
        set_types, extra_type, (card_min, card_max) = self.args
        r = {"type": "array"}
        if card_min is not None:
            r['minItems'] = card_min
        if card_max is not None:
            r['maxItems'] = card_max
            if card_max > len(set_types) and extra_type is False:
                extra_type = True  # Cardinals trump lack of allowed extras
        if set_types:  # Tuple array
            r['items'] = [t.tojson() for t in set_types]
            if extra_type is False:  # No extra items allowed
                r['additionalItems'] = False
            elif extra_type is True:  # Extra items with any type
                pass
            else:  # Forced type for extra items
                r['additionalItems'] = extra_type.tojson()
        else:  # List array
            assert extra_type not in (True, False)
            r['items'] = extra_type.tojson()
        return r
