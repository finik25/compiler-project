import sys
import argparse
import sys
import os
# Добавляем корень проекта в путь поиска модулей
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.lexer.scanner import Scanner

def main():
    parser = argparse.ArgumentParser(description="MiniCompiler")
    subparsers = parser.add_subparsers(dest="command", required=True)

    lex_parser = subparsers.add_parser("lex", help="Run lexer")
    lex_parser.add_argument("--input", required=True, help="Input source file")

    args = parser.parse_args()

    if args.command == "lex":
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                source = f.read()
        except FileNotFoundError:
            print(f"Error: file '{args.input}' not found", file=sys.stderr)
            sys.exit(1)

        scanner = Scanner(source)
        while not scanner.is_at_end():
            token = scanner.next_token()
            print(token)
        # Print final EOF token
        print(scanner.next_token())

if __name__ == "__main__":
    main()