JsonSchema Compact Notation
===========================

[Json-schema](https://json-schema.org/understanding-json-schema/reference/)
is very useful to document and validate inputs and outputs of
JSON-based REST APIs. Unfortunately, the schemas are more verbose and
less human-readable than one may wish. This library defines a more
compact syntax to describe JSON schemas, as well as a parser to
convert such specifications into actual JSON schema.

At some point in the future, this library may also offer the way back,
from JSON schemas back to a compact notation.

Informal grammar
----------------

Litteral JSON types are accessible as keywords: `boolean`, `string`,
`integer`, `number`, `null`.

Regular expression strings are represented by `r`-prefixed litteral
strings, similar to Python litterals: `r"[0-9]+"` converts into
`{"type": "string", "pattern": "[0-9]+"}`.

Regular expression strings are represented by `f`-prefixed litteral
strings: `f"uri""` converts into `{"type": "string", "format":
"uri"}`.

JSON constants are introduced between back-quotes: `` `123` ``
converts to `{"const": 123}`. If several constants are joined with an
`|` operator, they are translated into an enum: `` `1`|`2` `` converts
to `{"enum": [1, 2]}`.

Arrays are described between square brackets:

* `[]` describes every possible array, and can also be written `array`.
* an homogeneous, non-empty array of integers is denoted `[integer+]`
* an homogeneous array of integers is denoted `[integer*]`
* an array of two booleans is denoted `[boolean, boolean]`. It can also
  contain additional items after those two booleans.
* To prevent items other than those explicitly listed, add an `only`
  keyword at the beginning of the array: `[only boolean, boolean]`.
* arrays support cardinal suffix between braces: `[]{7}` is an
  array of 7 elements, `[integer*]{3,8}` is an array of between 3 and
  8 integers (inclusive), `[]{_, 9}` an array of at most 9
  elements, `[string*]{4, _}` an array of at least 4 strings.
* a uniqueness constraint can be added with the `unique` prefix, as in
  `[unique integer+]`, which will allow `[1, 2, 3]` but not `[1, 2, 1]`.

Strings and integers also support cardinal suffixes,
e.g. `string{16}`, `integer{_, 0xFFFF}`. Integer ranges as well as
sizes are inclusive.

Objects are described between curly braces:

* `{ }` describes every possible object, and can also be written
  `object`.
* `{"bar": integer}` is an object with one field `"bar"` of type
  integer, and possibly other fields.
* To prevent other fields from being accepted, use a prefix `only`, as in
  `{only "bar": integer}`.
* Quotes are optional around property names, if they are identifiers other
  than `"_"` or `"only"`: it's legal to write `{bar: integer}`.
* The wildcard property name `_` gives a type constraint on every
  extra property, e.g.  `{"bar": integer, _: string}` is an object
  with a field `"bar"` of type integer, and optionally other
  properties with any names, but all containing strings.
* Property names can be forced to respect a regular expression, with
  `only <regex>` prefix, e.g. `{only r"[0-9]+" _: integer}` will only
  accept integer-to-integer maps.


Types can be combined:

* with infix operator `&`: `A & B` is the type of objects which
  respect both schemas `A` and `B`.
* with infix operator `|`: `A | B` is the type of objects which
  respect at least one of the schemas `A` or `B`. `&` takes precedence
  over `|`, i.e. `A & B | C & D` is to be read as `(A&B) | (C&D)`.
* parentheses can be added, e.g. `A & (B|C) & D`

A top-level schema may contain definitions. They are listed after the
main schema, separated by a `where` keyword from it, and separated
from each other by `and`. References to definitions must appear
between angle bracket `<...>`. For instance, `{source: <id>, dest:
<id>} where id = r"[a-z]+"`.

More formally
-------------

    schema ::= type («where» identifier «=» type «and» ...)+

    type ::= type «&» type          # allOf those types; takes precedence over «|».
           | type «|» type          # anyOf those types.
           | «(» type «)»           # parentheses to enforce precedence.
           | «not» type             # anything but this type.
           | «`»json_litteral«`»    # just this JSON constant value.
           | «<»identifier«>»       # identifier refering to the matching top-level definition.
           | r"regular_expression"  # String matched by this regex.
           | f"format"              # json-schema draft7 string format.
           | «string» cardinal?     # a string, with this cardinal constraint on number of chars.
           | «integer» cardinal?    # an integer within the range described by cardinal.
           | «integer» «/» int      # an integer which must be multiple of that int.
           | «object»               # any object.
           | «array»                # any array.
           | «boolean»              # any boolean.
           | «null»                 # the null value.
           | «number»               # any number.
           | object                 # structurally described object.
           | array                  # structurally described array.

    cardinal ::= «{» int «}»        # Exactly that number of chars / items / properties.
               | «{» «_», int «}»   # At most that number of chars / items / properties.
               | «{» int, «_» «}»   # At least that number of chars / items / properties.
               | «{» int, int «}»   # A number of chars / items / properties within this range.


    object ::= «{» («only» regex?)? (object_key «?»? «:» type «,»...)* «}» cardinal?
             # if «only» occurs without a regex, no extra property is allowed.
             # if «only» occurs with a regex, all extra property names must match that regex.
             # if «?» occurs, the preceding property is optional, otherwise it's required.

    object_key ::= identifier    # Litteral property name.
                 | «"»string«"»  # Properties which aren't identifiers must be quoted.
                 | «_»           # Properties not explicitly listed must match the following type.

    array ::= «[» «only»? «unique»? (type «,»)* («*»|«+»|ø) «]» cardinal?
            # if «only» occurs, no extra item is allowed.
            # if «unique» occurs, each array item must be different from every other.
            # if «*» occurs, the last type can be repeated from 0 to any times.
            # Every extra item must be of that type.
            # if «+» occurs, the last type can be repeated from 1 to any times.
            # Every extra item must be of that type.

    int ::= /0x[0-9a-FA-F]+/ | /[0-9]+/
    identifier ::= /[A-Za-z_][A-Za-z_0-9]*/

TODO
----

Some things that may be added in future versions

* on objects:
    * limited support for dependent object fields, e.g.
      `{"card_number": integer, "billing_address" if "card_number":
      string, ...}`.
* on numbers:
    * ranges over floats (reusing cardinal grammar with float boundaries)
    * modulus constrains on floats `number/0.25`.
    * exclusive ranges in addition to inclusive ones. May use returned
      braces, e.g. `integer{0,0x100{` as an equivalent for
      `integer{0,0xFF}`?
    * ranges alone are treated as integer ranges, i.e. `{1, 5}` is a shortcut
      for `integer{1, 5}`? Not sure whether it enhances readability, and there
      would be a need for float support in ranges then.
* combine string constraints: regex, format, cardinals... This can
  already be achieved with operator `&`.
* add a few `"$comment"` fields for non-obvious translations. Use size of
  notation vs. size of generated schema as a clue, plus the presence of such
  a somment at a higher level in the tree.
* support for `|`, `&` and `not` operators at Python's level? That would mean
  exposing the resulting parse tree, whereas currently I directly export some
  JSON. Would mosly make sens if schema simplification is supported.
* optional marker: `foobar?` is equivalent to `foobar|null`.
  Not sure whether it's worth it, the difference between a missing field and
  a field holding `null` is most commonly not significant.

Usage
-----

From Python:

    >>> import jsonschema_cn
    >>> jsonschema_cn.tojson("[integer, boolean+]{4}")
    '''{"$schema": "http://json-schema.org/draft-07/schema#",
        "type": "array",
        "minItems": 4,
        "maxItems": 4,
        "items": [{"type": "integer"}],
        "additionalItems": {"type": "boolean"},
    }'''

From command line:

    $ echo -n '[integer*]' | jscn -
    { "type": "array",
      "items": {"type": "integer"},
      "$schema": "http://json-schema.org/draft-07/schema#"
    }

    $ jscn --help
    usage: jscn [-h] [-v] [-o OUTPUT] [filename]

    Convert from a compact DSL into full JSON schema.

    positional arguments:
    filename              Input file; use '-' to read from stdin.

    optional arguments:
    -h, --help            show this help message and exit
    -v, --verbose         Verbose output
    -o OUTPUT, --output OUTPUT
    Output file; defaults to stdout

See also
--------

If you spend a lot of time dealing with complex JSON data structures,
you might also want to try [jsview](https://github.com/fab13n/jsview),
a smarter JSON formatter, which tries to effectively use both your
screen's width and height, by only inserting q carriage returns when
it makes sense:

    $ echo '{only codes: [<byte>+], id: r"[a-z]+", issued: f"date"}' > schema.cn

    $ cat schema.cn | jscn -
    {"type": "object", "required": ["codes", "id", "issued"], "properties": {
    "codes": {"type": "array", "items": [{"$ref": "#/definitions/byte"}], "ad
    ditionalItems": {"$ref": "#/definitions/byte"}}, "id": {"type": "string",
    "pattern": "[a-z]+"}, "issued": {"type": "string", "format": "date"}}, "a
    dditionalProperties": false, "$schema": "http://json-schema.org/draft-07/
    schema#"}

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
    "$schema": "http://json-schema.org/draft-07/schema#"
    }
