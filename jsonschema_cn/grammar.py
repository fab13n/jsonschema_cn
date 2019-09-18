"""x

Features unsupported by current grammar (those marked with an [X]
probably won't be addressed until after first release):

* number:
    * [X] multipleOf on non-integers
    * [X] exclusive ranges
* array:
    * `contains` predicates. Can add a `contains <type>` prefix where array
      items are expected. jsonschema doc seems dubious: "contains" is
      associated with an object rather than a list thereof.
    * uniqueItems flag. Can add `unique` keyword where array items are
      expected.
* string:
    * [X] combine regex / format / cardinal together. Can still be done
      with `allOf`.
* definitions and references. Can use Haskell's local definitions syntax
  `where foo = bar and baz = gnat`. Will have to be restricted to top-level.
  Should check that for dangling and unsed definitions.
* objects:
    * ability to forbid additionalProperties (by default unless there's
      a `...` suffix?)
    * [X] propertyNames constraints
    * [X] minProperties and maxProperties
    * [X] dependencies (TODO `"billing_address" if "credit_card": ...`)
    * [X] patternProperties. Can accept regex as property names.
    * [X] schema properties (not fully understood...)
* add source in `"$comment"` when sensible (criterion of size comparison?)
* [X] oneOf (dubious usefulness, compared to anyOf)
* not. Syntax: use a prefix `not`, it's not usefull enough to deserve a symbol.
* [X] `if / then / else`. Jsonschema doc seems dubious, shows them inside an
  object definition rather than in their own block.
* `"$schema": http://json-schema.org/draft-07/schema#` to be added on top-level

"""
from parsimonious import Grammar

grammar = Grammar(
    r"""
entry = _ sequence_or _
type = litteral / string / object / integer / array /
       lit_regex / lit_format / constant / parens
parens = lparen _ sequence_or _ rparen
sequence_or = sequence_and (_ or _ sequence_and)*
sequence_and = type (_ and _ type)*

litteral = "boolean" / "null" / "number"

lit_integer = ~"[0-9]+" / ~"0x[0-9a-fA-F]+"
lit_string = ~"\"[^\"]*\""  # TODO handle escaped quotes
lit_regex = regex_prefix lit_string
lit_format = format_prefix lit_string

constant = ~"`[^`]+`"

string = "string" _ opt_cardinal
integer = "integer" _ opt_cardinal _ opt_multiple
opt_multiple = ("/" _ lit_integer)?

regex_prefix = "r"
format_prefix = "f"
dots = "..."
or = "|"
and = "&"
lparen = "("
rparen = ")"
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
object_empty = lbrace _ dots? _ rbrace  # TODO optional comma before ...
object_non_empty = lbrace _ object_field (_ comma _ object_field)* _ rbrace
object_field = property_less_pair / field_pair / dots
property_less_pair = dots _ colon _ field_type
field_pair = lit_string _ question? _ colon _ field_type
field_type = type / dots

array = array_empty / array_non_empty
array_empty = lbracket _ dots? _ rbracket _ opt_cardinal
array_non_empty = lbracket _ type (_ comma _ type)* _
                  array_extra _ rbracket _ opt_cardinal
array_extra = ((comma _ dots) / dots / plus / star)?

_ = meaninglessness*
meaninglessness = ~r"\s+" / comment
comment = ~r"#[^\r\n]*"
"""
)
