"""x

Features unsupported by current grammar (those marked with an [X]
probably won't be addressed until after first release):

* whitespaces aren't tolerated in most places.
* number:
    * [X] multipleOf on non-integers
    * [X] exclusive ranges
* array:
    * [X] contains predicates. Can add a `contains <type>` prefix where array
      items are expected. jsonschema doc seems dubious: "contains" is associated
      with an object rather than a list thereof.
    * [X] uniqueItems flag. Can add `unique` keyword where array items are expected.
* string:
    * regex. Can reuse parsimonious' tilde-prefix-on-strinf notation.
    * format
* definitions and references. Can use Haskell's local definitions syntax
  `where foo = bar and baz = gnat`. Will have to be restricted to top-level.
* objects:
    * ability to forbid additionalProperties (by default unless there's a `...` suffix?)
    * [X] propertyNames constraints
    * [X] minProperties and maxProperties
    * [X] dependencies (TODO `"billing_address" if "credit_card": ...`)
    * [X] patternProperties. Can accept regex as property names.
    * [X] schema properties (not fully understood...)
* add source in `"$comment"` when sensible (criterion of size comparison?)
* const. Syntax: just put them into back-quotes.
* enum: to be produced as an optimization of `{ "anyOf": [{ "const": ... } ... ] }`.
* anyOf, allOf. Syntax: use infix `|` and `&`. Don't introduce precedence, enforce
  parentheses instead.
* [X] oneOf (dubious usefulness)
* not. Syntax: use a prefix `not`, it's not usefull enough to deserve a symbol.
* [X] `if / then / else`. Jsonschema doc seems dubious, shows them inside an object
  definition rather than in their own block.
* `"$schema": http://json-schema.org/draft-07/schema#` to be added on top-level

"""
from parsimonious import Grammar

grammar = Grammar(r"""
entry = type ws*
ws = ~"\s"*
type = litteral / string / object / integer / array
litteral = "boolean" / "null" / "number"

int = ~"[0-9]+" / ~"0x[0-9a-f]+"

string = "string" opt_cardinal
integer = "integer" opt_cardinal opt_multiple
opt_multiple = ("/" int)?
key = ~"\"[^\"]*\""

dots = "..."
lbrace = "{"
rbrace = "}"
lbracket = "["
rbracket = "]"
comma = ","
colon = ":"
question = "?"
star = "*"
plus = "+"

opt_cardinal = (lbrace card_content rbrace)?
card_content = card_2 / card_min / card_max / card_1
card_2 = int comma int
card_1 = int
card_min = int comma? dots
card_max = dots comma? int

object = object_empty / object_non_empty
object_empty = lbrace dots? rbrace
object_non_empty = lbrace object_field (comma object_field)* rbrace
object_field = keyless_pair / field_pair / dots
keyless_pair = dots colon field_type
field_pair = key question? colon field_type
field_type = type / dots

array = array_empty / array_non_empty
array_empty = lbracket dots? rbracket opt_cardinal
array_non_empty = lbracket type (comma type)* array_extra rbracket opt_cardinal
array_extra = ((comma dots) / dots / plus / star)?

# TODO insert support for whitespaces
_ = meaninglessness*
meaninglessness = ~r"\s+" / comment
comment = ~r"#[^\r\n]*"

""")
