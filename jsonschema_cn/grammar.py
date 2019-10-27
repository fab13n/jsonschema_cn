"""PEG Grammar for JSON-Schema compact notation."""
from parsimonious import Grammar

grammar = Grammar(r"""
schema = _ type _ opt_definitions _
type = sequence_and (_ or _ sequence_and)*
sequence_and = simple_type (_ and _ simple_type)*
simple_type = litteral / kw_forbidden / string / object / integer / array /
       lit_regex / lit_format / constant / parens / not_type / def_reference /
       conditional
parens = lparen _ type _ rparen

litteral = "boolean" / "null" / "number"

lit_integer =  ~"0x[0-9a-fA-F]+" / ~"[0-9]+"
lit_regex = regex_prefix lit_string
lit_format = format_prefix lit_string

lit_string = quote_char (non_quote_char*) quote_char

quote_char = "\""
backslash_char = "\\"
non_quote_char = escaped_char / ~"[^\"]"
escaped_char = backslash_char ~"."

constant = backquote_constant / lit_string
backquote_constant = backquote_char (neither_quote_nor_backquote / lit_string)* backquote_char
backquote_char = "`"
neither_quote_nor_backquote = escaped_char / (~"[^\"`]")

string = "string" _ opt_cardinal
integer = "integer" _ opt_cardinal _ opt_multiple
opt_multiple = ("/" _ lit_integer)?

not_type = kw_not _ simple_type

regex_prefix = "r"
format_prefix = "f"
wildcard = "_"
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
kw_forbidden = "forbidden"
kw_if = "if"
kw_then = "then"
kw_elif = "elif"
kw_else = "else"
kw_not = "not"
kw_object = "object"
kw_only = "only"
kw_unique = "unique"

conditional =
    kw_if _ type _ kw_then _ type
    (_ kw_elif _ type _ kw_then _ type)*
    (_ kw_else _ type)?

opt_cardinal = (lbrace _ card_content _ rbrace)?
card_content = card_2 / card_min / card_max / card_1
card_2 = lit_integer _ comma _ lit_integer
card_1 = lit_integer
card_min = lit_integer _ comma? _ wildcard
card_max = wildcard _ comma? _ lit_integer

object = object_empty / object_non_empty / object_keyword
object_empty = lbrace _ object_only _ rbrace opt_cardinal
object_keyword = kw_object opt_cardinal
object_non_empty = lbrace _
                   object_only _
                   object_pair (_ comma _ object_pair)* _
                   rbrace
                   opt_cardinal
object_only = (kw_only _ ((lit_regex/def_reference/wildcard) _ (colon _ type)?)? comma?)?
object_pair = object_pair_name _ question? _ colon _ object_pair_type
object_pair_name = lit_string / object_pair_unquoted_name
object_pair_unquoted_name = ~"[A-Za-z0-9][-_A-Za-z0-9]*"
object_pair_type = type / wildcard

array = array_empty / array_non_empty
array_empty = ((lbracket _ rbracket) / kw_array) _ opt_cardinal
array_non_empty = lbracket _ array_prefix _
                  type (_ comma _ type)* _
                  array_extra _
                  rbracket _
                  opt_cardinal
array_prefix = ((kw_only / kw_unique) _) *
array_extra = (plus / star)?

opt_definitions = (def_where _ definitions)?
definitions = _ definition (_ def_and _ definition)* _
definition = "<"? def_identifier ">"? _ def_equal _ type
def_where = "where"
def_and = "and"
def_equal = "="
def_reference = "<" def_identifier ">"
def_identifier = ~"[A-Za-z_][-A-Za-z_0-9]*"

_ = meaninglessness*
meaninglessness = ~r"\s+" / comment
comment = ~r"#[^\r\n]*"
"""
)
