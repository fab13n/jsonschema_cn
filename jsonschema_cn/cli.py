import sys
import json

from .grammar import grammar
from .visitor import JSCNVisitor


def main():

    input = sys.stdin
    output = sys.stdout
    verbose = "-v" in sys.argv

    source = input.read()
    raw_tree = grammar.parse(source)
    visitor = JSCNVisitor()
    if verbose:
        print("Raw output:", raw_tree)
    parsed_tree = visitor.visit(raw_tree)
    if verbose:
        print("Parsed output:", parsed_tree)
        schema = parsed_tree.to_schema()
        print("Schema:", schema)
        result = json.dumps(schema)
    else:
        result = parsed_tree.to_json()

    output.write(result)
    output.flush()
