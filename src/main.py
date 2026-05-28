import json
import sys
import argparse
import os
from src.lexer.scanner import Scanner
from src.preprocessor.preprocessor import Preprocessor
from src.parser.ast_printer import ASTPrinter
from src.parser.ast_dot import ASTDotGenerator
from src.parser.ast_json import ASTJSONGenerator
from src.parser.parser import Parser
from src.semantic.analyzer import SemanticAnalyzer


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

    # Preprocessor command
    preproc_parser = subparsers.add_parser("preprocess", help="Run preprocessor only")
    preproc_parser.add_argument("--input", required=True, help="Input source file")
    preproc_parser.add_argument("--output", help="Output file (default: stdout)")

    # Parser command
    parse_parser = subparsers.add_parser("parse", help="Parse source file and output AST")
    parse_parser.add_argument("--input", required=True, help="Input source file")
    parse_parser.add_argument("--output", help="Output file (default: stdout)")
    parse_parser.add_argument("--format", choices=["text", "dot", "json"], default="text", help="AST output format")
    parse_parser.add_argument("--verbose", action="store_true", help="Show additional info")

    # Semantic check command
    check_parser = subparsers.add_parser("check", help="Run semantic analysis")
    check_parser.add_argument("--input", required=True, help="Input source file")
    check_parser.add_argument("--verbose", action="store_true", help="Show symbol table and decorated AST")
    check_parser.add_argument("--output", help="Output file for errors or report (optional)")

    # IR command
    ir_parser = subparsers.add_parser("ir", help="Generate Intermediate Representation (IR)")
    ir_parser.add_argument("--input", required=True, help="Input source file")
    ir_parser.add_argument("--output", help="Output file (default: stdout)")
    ir_parser.add_argument("--format", choices=["text", "dot", "json"], default="text", help="IR output format")
    ir_parser.add_argument("--stats", action="store_true", help="Show IR statistics")
    ir_parser.add_argument("--verbose", action="store_true", help="Show additional info")

    args = parser.parse_args()

    if args.command == "lex":
        try:
            with open(args.input, "r", encoding="utf-8-sig") as f:
                source = f.read()
        except FileNotFoundError:
            print(f"Error: file '{args.input}' not found", file=sys.stderr)
            sys.exit(1)

        if args.preprocess:
            preprocessor = Preprocessor(source)
            source = preprocessor.process()
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
        errors = preprocessor.get_errors()
        for line, col, msg in errors:
            print(f"Error at {args.input}:{line}:{col}: {msg}", file=sys.stderr)

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
        tokens.append(scanner.next_token())

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

    elif args.command == "check":
        try:
            with open(args.input, 'r', encoding='utf-8-sig') as f:
                source = f.read()
        except FileNotFoundError:
            print(f"Error: file '{args.input}' not found", file=sys.stderr)
            sys.exit(1)

        # Lexical analysis
        scanner = Scanner(source)
        tokens = []
        while not scanner.is_at_end():
            tokens.append(scanner.next_token())
        tokens.append(scanner.next_token())

        # Parsing
        parser = Parser(tokens)
        ast = parser.parse()

        if parser.errors:
            for err in parser.errors:
                print(f"Syntax error: {err}", file=sys.stderr)
            sys.exit(1)

        # Semantic analysis
        analyzer = SemanticAnalyzer()
        symtable, errors = analyzer.analyze(ast)

        output_lines = []
        if errors:
            for err in errors:
                output_lines.append(f"Semantic error: {err.message} at {err.line}:{err.column}")
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write("\n".join(output_lines))
            else:
                for line in output_lines:
                    print(line)
            sys.exit(1)
        else:
            output_lines.append(analyzer.get_report())
            if args.verbose:
                output_lines.append("\nDecorated AST:")
                printer = ASTPrinter()
                output_lines.append(printer.print_decorated(ast))
            report = "\n".join(output_lines)
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(report)
            else:
                print(report)

    elif args.command == "ir":
        try:
            with open(args.input, 'r', encoding='utf-8-sig') as f:
                source = f.read()
        except FileNotFoundError:
            print(f"Error: file '{args.input}' not found", file=sys.stderr)
            sys.exit(1)

        # Лексический анализ
        scanner = Scanner(source)
        tokens = []
        while not scanner.is_at_end():
            tokens.append(scanner.next_token())
        tokens.append(scanner.next_token())

        # Парсинг
        parser = Parser(tokens)
        ast = parser.parse()
        if parser.errors:
            for err in parser.errors:
                print(f"Syntax error: {err}", file=sys.stderr)
            sys.exit(1)

        # Семантический анализ (нужен для типов и символьной таблицы)
        analyzer = SemanticAnalyzer()
        symtable, errors = analyzer.analyze(ast)
        if errors:
            for err in errors:
                print(f"Semantic error: {err.message} at {err.line}:{err.column}", file=sys.stderr)
            sys.exit(1)

        # Генерация IR
        from src.ir import IRGenerator, IRPrinter, IRDotGenerator
        ir_gen = IRGenerator(symtable)
        program_ir = ir_gen.generate(ast)

        if args.verbose:
            # Выводим расширенную информацию (локальные переменные, etc.)
            printer = IRPrinter(verbose=True)
        else:
            printer = IRPrinter(verbose=False)

        if args.stats:
            total_instr = 0
            total_blocks = 0
            total_temps = 0
            for func in program_ir.functions:
                total_blocks += len(func.blocks)
                total_temps += func.temp_counter
                for blk in func.blocks:
                    total_instr += len(blk.instructions)
            stats = (
                f"IR Statistics:\n"
                f"  Functions: {len(program_ir.functions)}\n"
                f"  Basic blocks: {total_blocks}\n"
                f"  Instructions: {total_instr}\n"
                f"  Temporaries: {total_temps}"
            )
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(stats)
            else:
                print(stats)
            if not args.output and args.format != "text":
                # Если запрошена статистика и другой формат, выводим её в stderr
                print(stats, file=sys.stderr)

        # Форматирование вывода
        if args.format == "text":
            printer = IRPrinter(verbose=args.verbose)
            output = printer.print_program(program_ir)
        elif args.format == "dot":
            dot_gen = IRDotGenerator()
            output = dot_gen.generate(program_ir)
        elif args.format == "json":
            from src.ir.ir_json import IRJSONGenerator
            json_gen = IRJSONGenerator()
            output = json_gen.generate(program_ir)
        else:
            output = ""

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
        else:
            print(output)

if __name__ == "__main__":
    main()