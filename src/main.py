import sys
import argparse
import os
from src.lexer.scanner import Scanner
from src.preprocessor.preprocessor import Preprocessor
from src.parser.ast_printer import ASTPrinter
from src.parser.ast_dot import ASTDotGenerator
from src.parser.ast_json import ASTJSONGenerator
from src.parser.parser import Parser


def main():
    parser = argparse.ArgumentParser(description="MiniCompiler")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Lexer command
    lex_parser = subparsers.add_parser("lex", help="Run lexer")
    lex_parser.add_argument("--input", required=True, help="Input source file")
    lex_parser.add_argument("--preprocess", action="store_true",
                            help="Run preprocessor before lexing")
    lex_parser.add_argument("--show-preprocessed", action="store_true",
                            help="Show preprocessed source and exit")

    # Preprocessor command (new)
    preproc_parser = subparsers.add_parser("preprocess", help="Run preprocessor only")
    preproc_parser.add_argument("--input", required=True, help="Input source file")
    preproc_parser.add_argument("--output", help="Output file (default: stdout)")


    parse_parser = subparsers.add_parser("parse", help="Parse source file and output AST")
    parse_parser.add_argument("--input", required=True, help="Input source file")
    parse_parser.add_argument("--output", help="Output file (default: stdout)")
    parse_parser.add_argument("--format", choices=["text", "dot", "json"], default="text", help="AST output format")
    parse_parser.add_argument("--verbose", action="store_true", help="Show additional info")

    args = parser.parse_args()

    if args.command == "lex":
        try:
            with open(args.input, "r", encoding="utf-8-sig") as f:
                source = f.read()
        except FileNotFoundError:
            print(f"Error: file '{args.input}' not found", file=sys.stderr)
            sys.exit(1)

        # Run preprocessor if requested
        if args.preprocess:
            preprocessor = Preprocessor(source)
            source = preprocessor.process()

            # Check for preprocessor errors
            errors = preprocessor.get_errors()
            for line, col, msg in errors:
                print(f"Preprocessor error at {args.input}:{line}:{col}: {msg}",
                      file=sys.stderr)

            if args.show_preprocessed:
                print(source)
                return

            if errors:
                print("Preprocessing failed with errors", file=sys.stderr)
                sys.exit(1)

        # Run lexer
        scanner = Scanner(source)
        while not scanner.is_at_end():
            token = scanner.next_token()
            print(token)
        print(scanner.next_token())

    elif args.command == "preprocess":
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                source = f.read()
        except FileNotFoundError:
            print(f"Error: file '{args.input}' not found", file=sys.stderr)
            sys.exit(1)

        preprocessor = Preprocessor(source)
        result = preprocessor.process()

        # Report errors
        errors = preprocessor.get_errors()
        for line, col, msg in errors:
            print(f"Error at {args.input}:{line}:{col}: {msg}", file=sys.stderr)

        # Output result
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(result)
        else:
            print(result)


    elif args.command == "parse":

        try:
            with open(args.input, 'r', encoding='utf-8-sig') as f:
                source = f.read()

        except FileNotFoundError:
            print(f"Error: file '{args.input}' not found", file=sys.stderr)
            sys.exit(1)

        scanner = Scanner(source)
        tokens = []

        while not scanner.is_at_end():
            tokens.append(scanner.next_token())

        tokens.append(scanner.next_token())  # EOF
        parser = Parser(tokens)
        ast = parser.parse()

        if parser.errors:

            for err in parser.errors:
                print(f"Syntax error: {err}", file=sys.stderr)

            if args.verbose:
                print("Parsing completed with errors.", file=sys.stderr)

        printer = ASTPrinter(verbose=args.verbose)

        if args.format == "text":
            output = printer.print_text(ast)

        elif args.format == "dot":
            dot_gen = ASTDotGenerator()
            output = dot_gen.generate(ast)

        elif args.format == "json":
            json_gen = ASTJSONGenerator()
            output = json_gen.generate(ast, indent=2)

        else:
            output = ""

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
        else:
            print(output)


if __name__ == "__main__":
    main()