"""x

Features unsupported by current grammar (those marked with an [X]
probably won't be addressed until after first release):

* number:
    * [X] multipleOf on non-integers
    * [X] exclusive ranges
* array:
    * `contains` predicates. Can add a `contains <type>` prefix where array
      items are expected. jsonschema doc seems dubious: "contains" is associated
      with an object rather than a list thereof.
    * uniqueItems flag. Can add `unique` keyword where array items are expected.
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
entry = _ type _
type = litteral / string / object / integer / array
litteral = "boolean" / "null" / "number"

lit_integer = ~"[0-9]+" / ~"0x[0-9a-f]+"

string = "string" _ opt_cardinal
lit_string = ~"\"[^\"]*\""  # TODO handle escaped quotes
integer = "integer" _ opt_cardinal _ opt_multiple
opt_multiple = ("/" _ lit_integer)?

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

opt_cardinal = (lbrace _ card_content _ rbrace)?
card_content = card_2 / card_min / card_max / card_1
card_2 = lit_integer _ comma _ lit_integer
card_1 = lit_integer
card_min = lit_integer _ comma? _ dots
card_max = dots _ comma? _ lit_integer

object = object_empty / object_non_empty
object_empty = lbrace _ dots? _ rbrace
object_non_empty = lbrace _ object_field (_ comma _ object_field)* _ rbrace
object_field = property_less_pair / field_pair / dots
property_less_pair = dots _ colon _ field_type
field_pair = lit_string _ question? _ colon _ field_type
field_type = type / dots

array = array_empty / array_non_empty
array_empty = lbracket _ dots? _ rbracket _ opt_cardinal
array_non_empty = lbracket _ type (_ comma _ type)* _ array_extra _ rbracket _ opt_cardinal
array_extra = ((comma _ dots) / dots / plus / star)?

_ = meaninglessness*
meaninglessness = ~r"\s+" / comment
comment = ~r"#[^\r\n]*"
""")
