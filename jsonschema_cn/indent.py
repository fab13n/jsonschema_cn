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
