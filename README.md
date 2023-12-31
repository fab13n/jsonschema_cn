JsonSchema Compact Notation
===========================

[JSON Schema](https://json-schema.org/) is very useful to document and
validate inputs and outputs of JSON-based REST APIs. If you check
everything that goes into your program (requests, configuration
files…) and everything that goes out of it (responses), you'll catch a
lot of errors and regressions early.  Moreover, the schema also acts
has a documentation for develpers and users alike, and a documentation
that _has_ to stay up-to-date: otherwise you get exceptions thrown
around!

Unfortunately, IMO JSON Schema is neither as concise nor as
human-readable as it should. Not as bad as XML schemas, but not great
either. As a demonstration, here's a schema for a tiny subset of
[GeoJSON](https://tools.ietf.org/html/rfc7946):


	{ "type": "object",
      "required": ["type", "geometry"],
      "properties": {
        "type": {"const": "Feature"},
        "geometry": {
          "anyOf": [
            {"$ref": "#/definitions/point"},
            {"$ref": "#/definitions/lineString"}]}},
      "definitions": {
        "coord": {
          "type": "array",
          "items": {"type": "number"},
          "minItems": 2, "maxItems": 2},
        "point": {
          "type": "object",
          "required": ["type", "coordinates"],
          "properties": {
            "type": {"const": "Point"},
            "coordinates": {"$ref": "#/definitions/coord"}}},
        "lineString": {
          "type": "object",
          "required": ["type", "coordinates"],
          "properties": {
            "type": {"const": "LineString"},
            "coordinates": {
              "type": "array",
              "items": {"$ref": "#/definitions/coord"}}}}}}

Enter JSCN, a.k.a. "JSON Schema Compact Notation", which expresses the
exact same schema as follows:

    { 
      type: "Feature", 
      geometry: <point> | <lineString>
    }
    where coord      = [number*]{2}
      and point      = {type: "Point", coordinates: <coord>}
      and lineString = {type: "LineString", coordinates: [<coord>*]}

Not only is it much shorter; hopefully it reads as well as an
informal documentation written for fellow developers.

JSCN allows to express most of JSON Schema, in a language which isn't
a subset of JSON, but is much more compact and human-readable. This
Python library implements a parser which translates JSCN into
JSON Schema, and encapsulates the result in a Python object allowing
actual validation through [the JSON Schema
library](https://python-jsonschema.readthedocs.io/).

Below is an informal description of the grammar. Fluency with JSON is
expected; familiarity with JSON Schema is probably not mandatory, but
won't hurt.

Informal grammar
----------------

### simple types

Litteral JSON types are accessible as keywords: `boolean`, `string`,
`integer`, `number`, `null`.

Regular expression strings are represented by `r`-prefixed litteral
strings, similar to Python's litterals: `r"^[0-9]+$"` converts into
`{"type": "string", "pattern": "^[0-9]+$"}` and matches strings which
conform to the regular expression. Beware that for JSON Schema, partial
matches are OK, for instance `r"[0-9]+"` does match `"foo123bar"`. Add
`"^…$"` markers to match the whole string.


Predefined string formats are represented by `f`-prefixed litteral
strings: `f"uri"` converts into `{"type": "string", "format":
"uri"}`. The list of currently predefined formats can be found for
instance at
[https://json-schema.org/understanding-json-schema/reference/string.html#format].

JSON constants are introduced between back-quotes: `` `123` ``
converts to `{"const": 123}` and will only match the number 123. If
several constants are joined with an `|` operator, they are translated
into a JSON Schema enum: `` `1`|`2` `` converts to `{"enum": [1,
2]}`. For litteral constants (strings, numbers, booleans, null),
backquotes aren't mandatory, i.e. `` `"foo"` `` and `"foo"` are
equivalent.

### Arrays

Arrays are described between square brackets:

* `[]` matches every possible array, and can also be written `array`.
* An homogeneous, non-empty array of integers is denoted `[integer+]`
* An homogeneous, possibly empty array of integers is denoted `[integer*]`
* An array starting with two booleans is denoted `[boolean, boolean]`.
  It can also contain additional items after those two booleans, and those
  items don't have to be booleans.
* In order to forbid additional items, add an `only` keyword at the beginning
  of the array: `[only boolean, boolean]` will reject `[true, false, 1]`,
  whereas `[boolean, boolean]` would have accepted it.
* Arrays support cardinal suffix between braces: `[]{7}` is an array
  with exactly 7 elements, `[integer*]{3,8}` is an array with between 3
  and 8 integers (inclusive), `[]{_, 9}` an array with at most 9
  elements, `[string*]{4, _}` an array with at least 4 strings.
* A uniqueness constraint can be added with the `unique` prefix, as in
  `[unique integer+]`, which accepts `[1, 2, 3]` but not `[1, 2, 1]`
  since `1` occurs more than once.

Strings and integers also support cardinal suffixes, e.g. `string{16}`
(a string of 16 characters), `integer{_, 0xFFFF}` (an integer between
0 and 65533). Ranges and sizes are inclusive.

### Objects

Objects are described between curly braces:

* `{ }` matches every possible object, and can also be written
  `object`.
* `{"bar": integer}` is an object with one field `"bar"` of type
  integer, and possibly other fields.
* Quotes are optional around property names, if they are are valid
  JavaScript identifiers other than `"_"` or `"only"`: it's legal to
  write `{bar: integer}`.
* To prevent non-listed property names from being accepted, use a
  prefix `only` just after the opening brace, as in `{only "bar":
  integer}`.
* Property names can be forced to comply with a regex, by an `only
  r"regex"` prefix, which can also be a reference to a definition:
  `{only r"^[a-z]+$"}`, or the equivalent `{only <word>} where
  word=r"^[a-z]$"+`.  Beware that according to JSON Schema, even
  explicitly listed property names must comply with the regex. For
  instance, nothing can satisfy the schema `{only r"^[0-9]+$",
  "except_this": _}`, because `r"^[0-9]+$"` doesn't match
  `"except_this"`.  To circumvent this limitation, you need to widen
  the regex with an `"|"`, e.g.  `{only r"^([0-9]+|except_this)$"}`,
  or ``{only <key>} where key = `"except_this"` | r"^[0-9]+$"``.
* In addition to enforcing a regex on property names, one can also
  enforce a type constraint on the associated values: `{only <word>:
  integer}`. If you want a constraint on the type but not on the name,
  the name can be replaced by an underscore wildcard: `{only _:
  integer}`.
* A special type `forbidden`, equivalent to JSON Schema's `false`, can
  be used to specifically forbid a property name: `{reserved_name?:
  forbidden}`. Notice that the question mark is mandatory: otherwise,
  it would both expect the property to exist, and accept no value in it.

### Definitions

Definitions can be used in the schema, and given with a suffix `where 
name0 = def0 and ... and nameX=defX`. References to definitions are
put between angles, for instance `{author: <user_name>} where 
user_name = r"^\w+$"`. When dumping the schema into actual JSON Schema,
unused definitions are pruned, and missing definitions cause an error.
Definitions can only occur at top-level, i.e. 
`{foo: <bar>} where bar=number` is legal, but
`{foo: (<bar> where bar=number)}` is not.


### Operations between types

Types can be combined:

* With infix operator `&`: `A & B` is the type of objects which
  respect both schemas `A` and `B`.
* With infix operator `|`: `A | B` is the type of objects which
  respect at least one of the schemas `A` or `B`. `&` takes precedence
  over `|`, i.e. `A & B | C & D` is to be read as `(A&B) | (C&D)`.
* With conditional expressions: `if A then B elif C then D else E`
  will enforce constraint `B` if constraint `A` is met, enforce `D` if
  `C` is met, or enforce `E` if neither `A` nor `C` are met. `elif`
  and `else` parts are optional. For instance, `if {country: "USA"}
  then {postcode: r"\d{5}(-\d{4})?"} else {postcode: string}` will
  only check the postcode with the regex if the country is `"USA"`.
* Parentheses can be added to enforce precedences , e.g. `A & (B|C) & D`
* There is also an `not` operator: `{foo: not boolean}`.

### From Python

Combinations can also be performed on Python objects, e.g. the
following Python expression is OK: `Schema("{foo: number}") |
Schema("{bar: number}")`, and produces a schema equivalent to
`Schema("{foo: number}|{bar: number}")`.  When definitions are merged
in Python with `|` or `&`, their definitions are merged as needed. If
a definition appears on both sides, it must be equal, i.e. one can
merge `{foo: <n>} where n=number` with `{bar: <n>} where n=number` but
not with `{foo: <n>} where n=integer`.

More formally
-------------

    schema ::= type («where» definitions)?

    definitions ::= identifier «=» type («and» identifier «=» type)*

    type ::= type «&» type          # allOf those types; takes precedence over «|».
           | type «|» type          # anyOf those types.
           | «(» type «)»           # parentheses to enforce precedence.
           | «not» type             # anything but this type.
           | «`»json_litteral«`»    # just this JSON constant value.
           | «<»identifier«>»       # identifier refering to the matching top-level definition.
           | r"regular_expression"  # String matched by this regex.
           | f"format"              # JSON Schema draft7 string format.
           | «string» cardinal?     # a string, with this cardinal constraint on number of chars.
           | «integer» cardinal?    # an integer within the range described by cardinal.
           | «integer» «/» int      # an integer which must be multiple of that int.
           | «object»               # any object.
           | «array»                # any array.
           | «boolean»              # any boolean.
           | «null»                 # the null value.
           | «number»               # any number.
           | «forbidden»            # empty type (used mostly to disallow a property name).
           | object                 # structurally described object.
           | array                  # structurally described array.
           | conditional            # conditional if/then/else rule

    cardinal ::= «{» int «}»        # Exactly that number of chars / items / properties.
               | «{» «_», int «}»   # At most that number of chars / items / properties.
               | «{» int, «_» «}»   # At least that number of chars / items / properties.
               | «{» int, int «}»   # A number of chars / items / properties within this range.


    object ::= «{» object_restriction? (object_key «?»? «:» type «,»...)* «}» cardinal?
             # if «only» occurs without a regex, no extra property is allowed.
             # if «only» occurs with a regex, all extra property names must match that regex.
             # if «?» occurs, the preceding property is optional, otherwise it's required.

    object_restriction ::= ø
                         # Only explicitly listed property names are accepted:
                         | «only»
                         # every property name must conform to regex/reference:
                         | «only» (r"regex" | «<»identifier«>»)
                         # non-listed property names must conform to regex, values to type:
                         | «only» (r"regex" | «<»identifier«>» | «_»)«:» type

    object_key ::= identifier    # Litteral property name.
                 | «"»string«"»  # Properties which aren't identifiers must be quoted.

    array ::= «[» «only»? «unique»? (type «,»)* («*»|«+»|ø) «]» cardinal?
            # if «only» occurs, no extra item is allowed.
            # if «unique» occurs, each array item must be different from every other.
            # if «*» occurs, the last type can be repeated from 0 to any times.
            # Every extra item must be of that type.
            # if «+» occurs, the last type can be repeated from 1 to any times.
            # Every extra item must be of that type.

    conditional ::= «if» type «then» type («elif» type «then» type)* («else» type)?

    int ::= /0x[0-9a-fA-F]+/ | /[0-9]+/
    identifier ::= /[A-Za-z_][A-Za-z_0-9]*/



TODO
----

Some things that may be added in future versions:

* on numbers:
    * ranges over floats (reusing cardinal grammar with float
      boundaries)
    * modulus constraints on floats `number/0.25`.
    * exclusive ranges in addition to inclusive ones. May use returned
      braces, e.g. `integer{0,0x100{` as an equivalent for
      `integer{0,0xFF}`?
    * ranges alone are treated as integer ranges, i.e. `{1, 5}` is a
      shortcut for `integer{1, 5}`? Not sure whether it enhances
      readability, and there would be a need for float support in
      ranges then.
* combine string constraints: regex, format, cardinals...  This can
  already be achieved with operator `&`.
* try to embedded `#`-comments as `"$comment"`
* Implementation:
    * bubble up `?` markers in grammar to the top level.
* Syntax sugar:
    * optional marker: `foobar?` is equivalent to `foobar|null`.  Not
      sure whether it's worth it, the difference between a missing
      field and a field holding `null` is most commonly not significant.
    * check that references as `propertyNames` indeed point at string
      types.
    * make keyword case-insensitive?
    * treat `{foo: forbidden}` as `{foo?: forbidden}` as it's the only
      thing that would make sense?
* better error messages, on incorrect grammars, and on non-validating
  JSON data.
* reciprocal feature: try and translate a JSON Schema into a shorter
  and more readable JSCN source.

Usage
-----

### From command line

    $ echo -n '[integer*]' | jscn -
    { "type": "array",
      "items": {"type": "integer"},
      "$schema": "http://json-schema.org/draft-07/schema#"
    }

    $ jscn --help

    usage: jscn [-h] [-o OUTPUT] [-v] [--version] [filename]

    Convert from a compact DSL into full JSON Schema.

    positional arguments:
      filename              Input file; use '-' to read from stdin.

    optional arguments:
      -h, --help            show this help message and exit
      -o OUTPUT, --output OUTPUT
                            Output file; defaults to stdout
      -v, --verbose         Verbose output
      --version             Display version and exit

### From Python API

Python's `jsonschema_cn` package exports two main constructors:

* `Schema()`, which compiles a source string into a schema object;
* `Definitions()`, which compiles a source string (a sequence of
  definitions separated by keyword `and`, as in rule `definitions` of
  the formal grammar.

Schema objects have a `jsonschema` property, which contains the Python
dict of the corresponding JSON Schema.

Schemas can be combined with Python operators `&` (`"allOf"`) and `|`
(`"anyOf"`). When they have definitions, those definition sets are
merged, and definition names must not overlap.

Schemas can also be combined with definitions through `|`, and
definitions can be combined together also with `|`.

    >>> from jsonschema import Schema, Definitions

    >>> defs = Definitions("""
    >>>     id = r"[a-z]+" and
    >>>     byte = integer{0,0xff}
    >>> """)

    >>> s = Schema("{only <id>: <byte>}") | defs
    >>> s.jsonschema
    ValueError: Missing definition for byte

    >>> s = s | defs
    >>> s.jsonschema
    {"$schema": "http://json-schema.org/draft-07/schema#"
      "type": "object",
      "propertyNames": {"$ref": "#/definitions/id"},
      "additionalProperties": {"$ref": "#/definitions/byte"},
      "definitions": {
        "id":   {"type": "string", "pattern": "[a-z]+"},
        "byte": {"type": "integer", "minimum": 0, "maximum": 255}
      }
    }

    >>> Schema("[integer, boolean+]{4}").jsonschema
    { "$schema": "http://json-schema.org/draft-07/schema#",
      "type": "array",
      "minItems": 4, "maxItems": 4,
      "items": [{"type": "integer"}],
      "additionalItems": {"type": "boolean"},
    }

See also
--------

If you spend a lot of time dealing with complex JSON data structures,
you might also want to try [jsview](https://github.com/fab13n/jsview),
a smarter JSON formatter, which tries to effectively use both your
screen's width and height, by only inserting q carriage returns when
it makes sense:

    $ cat >schema.cn <<EOF

    { only codes: [<byte>+], id: r"[a-z]+", issued: f"date"}
    where byte = integer{0, 0xFF}
    EOF

    $ jscn schema.cn

    {"type": "object", "required": ["codes", "id", "issued"], "properties": {
    "codes": {"type": "array", "items": [{"$ref": "#/definitions/byte"}], "ad
    ditionalItems": {"$ref": "#/definitions/byte"}}, "id": {"type": "string",
    "pattern": "[a-z]+"}, "issued": {"type": "string", "format": "date"}}, "a
    dditionalProperties": false, "definitions": {"byte": {"type": "integer",
    "minimum": 0, "maximum": 255}}, "$schema": "http://json-schema.org/draft-
    07/schema#"}

    $ cat schema.cn | jscn - | jsview -

    {
      "type": "object",
      "required": ["codes", "id", "issued"],
      "properties": {
        "codes": {
          "type": "array",
          "items": [{"$ref": "#/definitions/byte"}],
          "additionalItems": {"$ref": "#/definitions/byte"}
        },
        "id": {"type": "string", "pattern": "[a-z]+"},
        "issued": {"type": "string", "format": "date"}
      },
      "additionalProperties": false,
      "definitions": {"byte": {"type": "integer", "minimum": 0, "maximum": 255}},
      "$schema": "http://json-schema.org/draft-07/schema#"
    }
