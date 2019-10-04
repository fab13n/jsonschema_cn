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

Litteral types are accessible as keywords: `boolean`, `string`,
`integer`, `number`, `null`.

Regular expression strings are represented by `r`-prefixed litteral
strings, similar to Python litterals: `r"[0-9]+"` converts into
`{"type": "string", "pattern": "[0-9]+"}`.

Regular expression strings are represented by `f`-prefixed litteral
strings: `f"uri""` converts into `{"type": "string", "format":
"uri"}`.

JSON constants are introduced between back-quotes: `` `123` ``
converts to `{"const": 123`}. If several constants are joined with an
`|` operator, they are translated into an enum: `` `1`|`2` `` converts to
`{"enum": [1, 2]}`.


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
e.g. `string{16}`, `integer{_, 0xFFFF}`.

Objects are described between curly braces:

* `{ }` describes every possible object, and can also be written
  `object`.
* `{"bar": integer}` is an object with one field `"bar"` of type
  integer, and possibly other fields.
* To prevent other fields from being accepted, use a prefix `only`, as in
  `{only "bar": integer}`.
* Quotes are optional around property names, is they are identifiers other
  than `"_"` or `"only"`: it's legal to write `{bar: integer}`.
* The wildcard property name `_` gives a type constraint on every
  extra property, e.g.  `{"bar": integer, _: string}` is an object
  with a field `"bar"` of type integer, and optionally other
  properties with any names, but all containing strings.
* Property names can be forced to respect a regular expression, with
`only <regex>` prefix, e.g. `{only r"[0-9]+" _: integer}` will only accept
integer-to-integer maps.


Types can be combined:

* with infix operator `&`: `A & B` is the type of objects which
  respect both schemas `A` and `B`.
* with infix operator `|`: `A | B` is the type of objects which
  respect at least one of the schemas `A` or `B`. `&` takes precedence
  over `|`, i.e. `A & B | C & D` is to be read as `(A&B) | (C&D)`.
* parentheses can be added, e.g. `A & (B|C) & D`

More formally
-------------

    schema ::= type («where» identifier «=» type «and» ...)+

    type ::= type & type            # allOf those types; takes precedence over «|».
           | type | type            # anyOf those types.
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
                 | «"»string«"»  # Propertoes which aren't identifier must be quoted.
                 | «_»           # Properties not explicitly listed must match the following type.

    array ::= «[» «only»? «unique»? (type «,»)* («*»|«+»|ø) «]» cardinal?
            # if «only» occurs, no extra item is allowed.
            # if «unique» occurs, each array item must be different from every other.
            # if «*» occurs, the last type can be repeated from 0 to any times.
            # Every extra item must be of that type.
            # if «+» occurs, the last type can be repeated from 1 to any times.
            # Every extra item must be of that type.

TODO
----

WILL DO:

* support for prefix `not`: `[not null*]` an array without null values.
* shared definitions: `{"source": <ident>, "destination": <ident>} where
  ident = r"[A-Z]{16}" and unused = boolean` will create and use an
  `ident` definition, create an `unused` definition without using it.

MAY DO:

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
  
WON'T DO:

* Support for `"oneOf"`. In my experience, `"anyOf"` is always enough.

Usage
-----

    >>> import jsonschema_cn
    >>> jsonschema_cn.tojson("[integer, boolean+]{4}")
    '''{"$schema": "http://json-schema.org/draft-07/schema#",
        "type": "array",
        "minItems": 4,
        "maxItems": 4,
        "items": [{"type": "integer"}],
        "additionalItems": {"type": "boolean"},
    }'''

Optimization notes
------------------

In the future, one might consider schema simplifications. Among things to be considered:

* Remplace `A&B` with `false` when `A` and `B` are incompatible
* Merge object constraints
* Merge arrays constraints? Not as obviously useful as object constraints
* Simplify cardinal constraints
* Perform the `const1 | ... | constn` to `enum` conversion as a simplification
* Remove `"type"` indicator when another key carries the constraint?
  (`"properties"`, `"items"`, `"format"`...)

From schema back to CN
----------------------

In the future, one might consider translating JSON Schemas back to
compact notations. Again, it moslty makes sens with CN-level
simplifications. This would be a two-step process:

* parse JSON-schema into a `tree.Type` Not clear whether there would
  be many cases of un-translatable schemas, nor whether a minimal tree
  representation would be easy to figure out. There's no canonical
  tree for a given schema, e.g. `[string, integer+]` and
  `[string, integer*]{2}` denote the same objects, and it's not
  obvious whether one is better than the other.

* print a tree back into source. This part should be more
  straightforward, offered as a method on `tree.Type` subclasses.
