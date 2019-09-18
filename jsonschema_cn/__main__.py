import sys
import json

from .grammar import grammar
from .visitor import JSCNVisitor


text = sys.stdin.read()
tree = grammar.parse(text)
visitor = JSCNVisitor()
print("Raw output:", tree)
output = visitor.visit(tree)
print("Parsed output:", output)
print("json:")
# print(output.tojson())
print(json.dumps(output.tojson()))
