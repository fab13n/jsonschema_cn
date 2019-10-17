import unittest
from . import Schema, Definitions
import json
import jsonschema


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

    def test_integer(self):
        self.cmp('integer{_,1}', {"type": "integer", "maximum": 1})
        self.cmp('integer{1,_}', {"type": "integer", "minimum": 1})
        self.cmp('integer{0,10}', {"type": "integer", "minimum": 0, "maximum": 10})
        self.cmp('integer/5', {"type": "integer", "multipleOf": 5})

    def test_string(self):
        self.cmp('string{_,1}', {"type": "string", "maxLength": 1})
        self.cmp('string{1,_}', {"type": "string", "minLength": 1})
        self.cmp('string{0,10}', {"type": "string", "minLength": 0, "maxLength": 10})

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

    def test_object_card(self):
        pass  # TODO

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
        pass  # TODO

    def test_where(self):
        s = '{only <id>: <byte>} where id = r"[a-z]+" and byte = integer{0,0xFF}'
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
            fleet: {only <id>: string}
        } where id = r"[a-z]+" """).to_jsonschema()

    def test_yyy(self):
        Schema("""
        { instance: <plid>,
          ground: <plid>,
          mission: <plid>,
          fleet: { only <plid>: <aircraft> }
        }
        where plid = r"[A-Z0-9]{4}"
        and aircraft = {
          color?: string,
          status?: string  # TODO bug in JSCN `"online"` | `"offline"`
        }
        """).to_jsonschema()

    def test_prune(self):
        s = Schema("""
        {prop: <used_1>}
        where used_1 = [<used_2>+]
        and unused_1 = [<unused_2>+]
        and used_2 = integer
        and unused_2 = string
        """)
        self.assertSetEqual(
            set(s.jsonschema['definitions'].keys()),
            {'used_1', 'used_2'}
        )

    def test_combine_1(self):
        s = Schema("""{prop: <used_1>}""")
        d = Definitions("""
        used_1 = [<used_2>+]
        and unused_1 = [<unused_2>+]
        and used_2 = integer
        and unused_2 = string
        """)
        s |= d
        self.assertSetEqual(
            set(s.jsonschema['definitions'].keys()),
            {'used_1', 'used_2'}
        )

    def test_combine_2(self):
        s = Schema("{prop: <used_1>}") | \
            Definitions("used_1 = [<used_2>+]") | \
            Definitions("unused_1 = [<unused_2>+]") | \
            Definitions("used_2 = integer") | \
            Definitions("unused_2 = string")
        self.assertSetEqual(
            set(s.jsonschema['definitions'].keys()),
            {'used_1', 'used_2'}
        )

    def test_combine_3(self):
        """combine defs together before adding the result to the schema."""
        s = Schema("{prop: <used_1>}") | (
            Definitions("used_1 = [<used_2>+]") |
            Definitions("unused_1 = [<unused_2>+]") |
            Definitions("used_2 = integer") |
            Definitions("unused_2 = string"))
        self.assertSetEqual(
            set(s.jsonschema['definitions'].keys()),
            {'used_1', 'used_2'}
        )

    def test_combine_schemas(self):
        self.cmp('{foo?: integer} & {bar?: string}',
                 {'allOf': [
                     {'properties': {'foo': {'type': 'integer'}},
                      'type': 'object'},
                     {'properties': {'bar': {'type': 'string'}},
                      'type': 'object'}]})


    def test_missing_def(self):
        with self.assertRaisesRegex(ValueError, "Missing definition"):
            Schema('{foo: <bar>}').to_jsonschema()

    def test_validate(self):
        s = Schema("{only x: integer}")
        s.validate()
        s.validate({"x": 1})
        with self.assertRaises(jsonschema.ValidationError):
            s.validate({"x": "1"})
        with self.assertRaises(jsonschema.ValidationError):
            s.validate({"x": 1, "y": 2})


    def test_def_conflict(self):
        with self.assertRaisesRegex(ValueError, "conflict"):
            Definitions("x = integer") | Definitions("x = string")


if __name__ == '__main__':
    unittest.main()
