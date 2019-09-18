JsonSchema Compact Notation
===========================

[Json-schema]() is very useful to document and validate inputs and outputs of JSON-based
REST APIs. Unfortunately, the schemas are more verbose and less human-readable than one
may wish. This library defines a more compact syntax to describe JSON schemas, as well
as a parser to convert such specifications into actual JSON schema.

At some point in the future, this library may also offer the way back, from JSON schemas
back to a compact notation.

Informal grammar
----------------

Litteral types are accessible as keywords: `boolean`, `string`,
`integer`, `number`, `null`.

Regular expression strings are represented by `r`-prefixed litteral
strings: `r"[0-9]+"` converts into `{"type": "string", "pattern":
"[0-9]+"}`.

Regular expression strings are represented by `f`-prefixed litteral
strings: `f"uri""` converts into `{"type": "string", "format":
"uri"}`.

JSON constants are introduced between back-quotes: `` `123` `` converts
to `123`.

Arrays are described between square brackets:

* an homogeneous, non-empty array of integers is denoted `[integer+]`
* an homogeneous array of integers is denoted `[integer*]`
* an array of two booleans is denoted `[boolean, boolean]`
* an array starting with two booleans and followed by any number
  of other items of any type is denoted with `[boolean, boolean, ...]`
* an array, without constraints on type nor number of items, is
  denoted `[...]`
* arrays support cardinal suffix between braces: `[...]{7}` is an
  array of 7 elements, `[integer*]{3,8}` is an array of between 3 and
  8 integers (inclusive), `[...]{...9}` an array of at most 9
  elements, `[string*]{4...}` an array of at least 4 strings. Beware,
  `[string]{4}` denotes nothing: it must be both an array of only one
  string(no `+` / `*` / `...' suffix) and an array of 4 elements.

Strings and integers also support cardinal suffixes, e.g. `string{16}`,
`integer{...0xFFFF}`.

Objects are described between curly braces:

* `{"bar": integer}` is an object with one field `"bar"` of type
  integer.
* `{"bar": integer, ...}` is an object with at least a field `"bar"`
  of type integer, plus any other possible field / type combination.
* `{"bar"?: integer, ...}` is an object which, if it has a field
  `"bar"`, has an integer in it. It may also have any other possible
  field / type combination.
* `{"bar": integer, ...: string}` is an object with a field
  `"bar"` of type integer. It may also have any other possible
  fields, but all of them must contain strings.

Types can be combined:

* with infix operator `&`: `A & B` is the type of objects which
  respect both schemas `A` and `B`.
* with infix operator `|`: `A | B` is the type of objects which
  respect at least one of the schemas `A` or `B`. `&` takes precedence
  over `|`, i.e. `A & B | C & D` is to be read as `(A&B) | (C&D)`.
* parentheses can be added, e.g. `A & (B|C) & D`

WILL DO:

* support for prefix `not`: `[not null*]` an array without null values.
* `contains` constraint on arrays, e.g. ``[boolean* contains `true`]``
  an array of booleans, at least one of them being true.
* `unique` constraint on arrays, e.g. `[integer* unique]` an array of integers
  without repetition.
* shared definitions: `{"source": *ident, "destination": *ident} where
  ident = r"[A-Z]{16}" and unused = boolean` will create and use an
  `"ident"` definition, create an `"unused"` definition without using it.

MAY DO:

* support for regex as object property names
* cardinal constraints for objects
* ranges for non-integral numbers
* combine string constraints: regex, format, cardinals... With can
  already be achieved with operator `&`.
* exclusive ranges for numbers (they are currently inclusive). May use
  returned braces, e.g. `integer{0,0x100{` as an equivalent for
  `integer{0,0xFF}`?
* add a few `"$comment"` fields for non-obvious translations.
* limited support for dependent object fields, e.g.  `{"card_number":
  integer, "billing_address" if "card_number": string, ...}`.
* support for `|`, `&` and `not` operators at Python's level? That would mean
  exposing the resulting parse tree, whereas currently I directly export some
  JSON.

Usage
-----

    >>> import jsonschema_cn
    >>> jsonschema_cn.tojson("[integer,boolean+]{4}")
    '''{"$schema": "http://json-schema.org/draft-07/schema#",
        "type": "array",
        "minItems": 4,
        "maxItems": 4,
        "items": [{"type": "integer"}],
        "additionalItems": {"type": "boolean"},
    }'''
