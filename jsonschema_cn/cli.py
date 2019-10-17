import sys
import json
from argparse import ArgumentParser

from .visitor import parse


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
    schema = parse('schema', source, verbose=args.verbose)
    try:
        # TODO Try and guess TTY width
        import jsview
        result = jsview.dumps(schema.jsonschema)
    except ModuleNotFoundError:
        # Raw printing if jsview isn't installed
        result = json.dumps(schema.jsonschema)

    output.write(result+"\n")
    output.flush()
