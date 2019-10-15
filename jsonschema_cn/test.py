import unittest
from . import Schema, Definitions
import json

class TestJSCN(unittest.TestCase):

    def cmp(self, src: str,sch: dict) -> None:
        sch2 = Schema(src).to_jsonschema()
        del sch2['$schema']
        self.assertDictEqual(sch2, sch)

    def test_simple(self):
        self.cmp("boolean", {"type": "boolean"})
        self.cmp("string", {"type": "string"})
        self.cmp("integer", {"type": "integer"})
        self.cmp("number", {"type": "number"})
        self.cmp("null", {"type": "null"})

    def test_lit_string(self):
        self.cmp('r"foo"', {"type": "string", "pattern": "foo"})
        self.cmp('f"foo"', {"type": "string", "format": "foo"})
        self.cmp('r"foo\\\"bar"', {"type": "string", "pattern": r'foo\"bar'})
        self.cmp('r"foo\\""', {"type": "string", "pattern": r'foo\"'})


    def test_constant(self):
        self.cmp("`123`", {"const": 123})
        self.cmp('`"123"`', {"const": "123"})
        self.cmp('`{"a": 1}`', {"const": {"a": 1}})

    def test_enum(self):
        self.cmp("`1`|`2`|`3`", {"enum": [1, 2, 3]})

    def test_object_empty(self):
        obj = {"type": "object"}
        self.cmp("{}", obj)
        self.cmp("object", obj)

    def test_object_simple(self):
        self.cmp("{only foo: integer}",
                 {"type": "object",
                  "required": ["foo"],
                  "properties":
                  {"foo": {"type": "integer"}},
                  "additionalProperties": False})
        self.cmp("{foo: integer}",
                 {"type": "object",
                  "required": ["foo"],
                  "properties":
                  {"foo": {"type": "integer"}}})
        self.cmp("{foo?: integer}",
                 {"type": "object",
                  "properties":
                  {"foo": {"type": "integer"}}})
        self.cmp('{"foo"?: integer}',
                 {"type": "object",
                  "properties":
                  {"foo": {"type": "integer"}}})
        self.cmp('{_: integer}',
                 {"type": "object",
                  "additionalProperties": {"type": "integer"}})

        # TODO combine wildcard + only: what's the meaning?!

    def test_object_card(self):
        pass

    def test_array_empty(self):
        array = {"type": "array"}
        self.cmp("[]", array)
        self.cmp("array", array)

    def test_object_simple(self):
        integer = {"type": "integer"}
        self.cmp("[only integer]",
                 {"type": "array",
                  "items": [integer],
                  "additionalItems": False})
        self.cmp("[integer]",
                 {"type": "array",
                  "items": [integer]})
        self.cmp("[integer*]",
                 {"type": "array",
                  "items": integer}) # List-notation rather than tuple notation
        self.cmp("[integer+]",  # Maybe encoded either that way or with a cardinal
                 {"type": "array",
                  "items": [integer],
                  "additionalItems": integer})

    def test_array_card(self):
        pass

    def test_where(self):
        s = '{only <id>, _: <byte>} where id = r"[a-z]+" and byte = integer{0,0xFF}'
        self.cmp(s, {
            'additionalProperties': {'$ref': '#/definitions/byte'},
            'definitions': {
                'byte': {'maximum': 255, 'minimum': 0, 'type': 'integer'},
                'id': {'pattern': '[a-z]+', 'type': 'string'}},
            'propertyNames': {'$ref': '#/definitions/id'},
            'type': 'object'
        })

    def test_xxx(self):
        Schema(r"""{
            kind: `"aircraft"`,
            mission: string
        } | {
            kind: `"mission"`,
            name: string,
            fleet: {only <id>, _: string}
        } where id = r"[a-z]+" """).to_jsonschema()

    def test_yyy(self):
        Schema("""
        { instance: <plid>,
          ground: <plid>,
          mission: <plid>,
          fleet: { only <plid> _: <aircraft> }
        }
        where plid = r"[A-Z0-9]{4}"
        and aircraft = {
          color?: string,
          status?: string  # TODO bug in JSCN `"online"` | `"offline"`
        }
        """).to_jsonschema()

if __name__ == '__main__':
    unittest.main()
