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
* Quotes are optional around property names, if they are identifiers other
  than `"_"` or `"only"`: it's legal to write `{bar: integer}`.
* To prevent non-listed property names from being accepted, use a
  prefix `only`, as in `{only "bar": integer}`.
* non-listed property names can be forced to follow a regex with an
  `only r"regex"` prefix, which can also be a reference to a
  definition: `{only r"[a-z]+"}`, `{only <word>, "except_this_one":
  integer} where word=r"[a-z]"+`.
* In addition to forcing non-listted property names, one can also
  force a type constraint on the associated values: `{only <word>:
  integer}`. If no naming constraint is desired, the name can be
  replace by an underscore wildcard: `{only _: integer}`.
* To restrict property names without forbidding additional ones, a
  prefix constraint `only <regex>` can be added, e.g. `{only r"[0-9]+"
  _: integer}` will only accept integer-to-integer maps. References to
  definitions are also accepted, as in `{only <int_string>} where
  int_string = r"[0-9]+"`. Beware that according to JSONSchema,
  explicitly listed properties must also respect the constraint.  So
  if you want your properties to include `"default"`, plus optional
  integers, you should specify ``{only <key>: {}, default: {}} where
  key = r"^[0-9]+$" | `"default"` ``.
* A special type `forbidden`, equivalent to JSONSchema's `false`, can
  be used to specifically forbid a property name: `{reserved_name?:
  forbidden}`. Notice that the question mark is mandatory: otherwise,
  it would both expect the property, and accept no value in it.

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

A top-level schema may contain definitions. They are listed after the
main schema, separated by a `where` keyword from it, and separated
from each other by `and`. References to definitions must appear
between angle bracket `<...>`. For instance, `{source: <id>, dest:
<id>} where id = r"[a-z]+"`.

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
           | f"format"              # json-schema draft7 string format.
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
                         # non-listed property names must conform to regex/reference:
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

    int ::= /0x[0-9a-FA-F]+/ | /[0-9]+/
    identifier ::= /[A-Za-z_][A-Za-z_0-9]*/



TODO
----

Some things that may be added in future versions:

* on objects:
    * limited support for dependent object fields, e.g.
      `{"card_number": integer, "billing_address" if "card_number":
      string, ...}`.
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
* add a few `"$comment"` fields for non-obvious translations. Use size
  of notation vs. size of generated schema as a clue, plus the
  presence of such a somment at a higher level in the tree.
* try to embedded `#`-comments as `"$comment"`? Gather them for each
  `or_sequence` and `'\n'`-join them on top?
* Implementation:
    * bubble up `?` markers in grammar to the top level.
* Syntax sugar:
    * optional marker: `foobar?` is equivalent to `foobar|null`.  Not
      sure whether it's worth it, the difference between a missing
      field and a field holding `null` is most commonly not
      significant.
    * check that references as `propertyNames` indeed point at string
      types.
    * make keyword case-insensitive?
    * treat `{foo: forbidden}` as `{foo?: forbidden}` as it's the only
      thing that would make sense?
* better error messages, on incorrect grammars, and on non-validating
  JSON data.
* reciprocal feature: try and translate a JSON-schema into a shorter
  and more readable JSCN source.

Usage
-----

From Python:



### From command line

    $ echo -n '[integer*]' | jscn -
    { "type": "array",
      "items": {"type": "integer"},
      "$schema": "http://json-schema.org/draft-07/schema#"
    }

    $ jscn --help

    usage: jscn [-h] [-o OUTPUT] [-v] [--version] [filename]

    Convert from a compact DSL into full JSON schema.

    positional arguments:
      filename              Input file; use '-' to read from stdin.

    optional arguments:
      -h, --help            show this help message and exit
      -o OUTPUT, --output OUTPUT
                            Output file; defaults to stdout
      -v, --verbose         Verbose output
      --version             Display version and exit

### From Python API

Python's `jsonschema_cn` packaga exports two main constructors:

* `Schema()`, which compiles a source string into a schema object;
* `Definitions()`, which compiles a source string (a sequence of
  definitions separated by keyword `and`, as in rule `definitions` of
  the formal grammar.

Schema objects have a `jsonschema` property, which contains the Python
dict of the corresponding JSON schema.

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
