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
    parser.add_argument('--version', action='store_const', const=True, default=False,
                        help="Display version and exit")
    args = parser.parse_args()

    if args.version:
        from . import __version__
        print(f"JSON Schema compact notation v{__version__}.")
        exit(0)

    input = open(args.filename, 'r') if args.filename != "-" else sys.stdin
    output = open(args.output, 'w') if args.output != "-" else sys.stdout

    source = input.read()
    raw_tree = grammar.parse(source)
    visitor = JSCNVisitor()
    if args.verbose:
        print("Raw output:", raw_tree)
    parsed_tree = visitor.visit(raw_tree)
    if args.verbose:
        print("Parsed output:", parsed_tree)
        schema = parsed_tree.to_jsonschema()
        print("Schema:", schema)
    else:
        schema = parsed_tree.to_jsonschema()

    try:
        # TODO Try and guess TTY width
        import jsview
        result = jsview.dumps(schema)
    except ModuleNotFoundError:
        result = json.dumps(schema)

    output.write(result+"\n")
    output.flush()
