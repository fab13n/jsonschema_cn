"""PEG Grammar for JSON-Schema compact notation."""
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

lit_integer =  ~"0x[0-9a-fA-F]+" / ~"[0-9]+"
lit_string = ~"\"([^\"\\\\]|\\\\.)*\""
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
kw_array = "array"
kw_object = "object"

opt_cardinal = (lbrace _ card_content _ rbrace)?
card_content = card_2 / card_min / card_max / card_1
card_2 = lit_integer _ comma _ lit_integer
card_1 = lit_integer
card_min = lit_integer _ comma? _ dots
card_max = dots _ comma? _ lit_integer

object = object_empty / object_non_empty
object_empty = ((lbrace _ object_extra _ rbrace) / kw_object) opt_cardinal
object_non_empty = lbrace _
                   object_property (_ comma _ object_property)* _
                   object_extra _
                   rbrace
                   opt_cardinal
object_property = object_unnamed_pair / object_pair
object_unnamed_pair = dots _ colon _ object_pair_type
object_pair = object_pair_name _ question? _ colon _ object_pair_type
object_pair_name = lit_string / object_pair_unquoted_name
object_pair_unquoted_name = ~"[A-Za-z0-9][-_A-Za-z0-9]*"
object_pair_type = type / dots
object_extra = comma? _ dots?

array = array_empty / array_non_empty
array_empty = ((lbracket _ dots? _ rbracket) / kw_array) _ opt_cardinal
array_non_empty = lbracket _
                  type (_ comma _ type)* _
                  array_extra _
                  rbracket _
                  opt_cardinal
array_extra = ((comma? _ dots) / plus / star)?

_ = meaninglessness*
meaninglessness = ~r"\s+" / comment
comment = ~r"#[^\r\n]*"
"""
)
