"""
When converting JSCN nodes into multi-line strings,
indentation book-keeping is removed, to keep code simpler.
This utility function reindents in a separate state.

TODO: string constants may contain unbalanced parenthese
      characters, which will throw off the indenter.
      Consider adding a state in the line parser which
      disregard special characters when in a string.
      This involves detecting double-quotes and backslashes
      before double-quotes.
"""

OPENING = set("[{(")
CLOSING = set("]})")

def indent(src, step=2):
    i = 0
    output = []
    for line in src.split("\n"):
        line = line.strip()
        j = 0
        for k in line:
            if k.isspace():
                pass
            elif k in CLOSING:
                i -= 1
            else:
                break
            j += 1
        output.append(" " * (i*step) + line)
        for k in line[j:]:
            if k in OPENING:
                i += 1
            elif k in CLOSING:
                i -= 1
    return "\n".join(output)
