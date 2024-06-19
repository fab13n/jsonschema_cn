import sys
import json
from argparse import ArgumentParser

from .parse import parse


def main():
    parser = ArgumentParser(
        description="Convert from a compact DSL into full JSON schema."
    )
    parser.add_argument(
        "-o", "--output", default="-", help="Output file; defaults to stdout"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_const",
        const=True,
        default=False,
        help="Verbose output",
    )
    parser.add_argument(
        "-s",
        "--source",
        action="store_const",
        const=True,
        default=False,
        help="Keep jscn source as a top-level comment",
    )
    parser.add_argument(
        "-r",
        "--reduce",
        action="store_const",
        const=True,
        default=False,
        help="Reduce variable references",
    )
    parser.add_argument(
        "-f",
        "--format",
        action="store_const",
        const=True,
        default=False,
        help="Reformat instead of compiling",
    )
    parser.add_argument(
        "filename",
        nargs="?",
        default="-",
        help="Input file; use '-' to read from stdin.",
    )
    parser.add_argument(
        "--version",
        action="store_const",
        const=True,
        default=False,
        help="Display version and exit",
    )
    args = parser.parse_args()

    if args.version:
        from . import __version__
        print(f"JSON Schema compact notation v{__version__}.")
        exit(0)

    input = open(args.filename, "r") if args.filename != "-" else sys.stdin
    output = open(args.output, "w") if args.output != "-" else sys.stdout

    source = input.read()
    try:
        schema = parse("schema", source, verbose=args.verbose)
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

    if args.reduce:
        from .beta import reduce as reduce
        schema = reduce(schema)

    if args.format:
        result = str(schema)
    else:
        json = schema.jsonschema
        if not args.source:
            del json["$comment"]
        try:
            # TODO Try and guess TTY width
            import jsview
            result = jsview.dumps(json)
        except ModuleNotFoundError:
            # Raw printing if jsview isn't installed
            result = json.dumps(json)

    output.write(result + "\n")
    output.flush()
