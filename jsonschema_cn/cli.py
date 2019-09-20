import sys
import json
from argparse import ArgumentParser

from .grammar import grammar
from .visitor import JSCNVisitor


def main():
    parser = ArgumentParser(description="Convert from a compact DSL into full JSON schema.")
    parser.add_argument('-o', '--output', default="-",
                        help="Output file; defaults to stdout")
    parser.add_argument('-v', '--verbose', action='store_const', const=True, default=False,
                        help="Verbose output")
    parser.add_argument('filename', nargs="?", default="-",
                        help="Input file; use '-' to read from stdin.")
    args = parser.parse_args()

    input = open(args.filename, 'r') if args.filename != "-" else sys.stdin
    output = open(args.output, 'w') if args.output != "-" else sys.stdout
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

    output.write(result+"\n")
    output.flush()
