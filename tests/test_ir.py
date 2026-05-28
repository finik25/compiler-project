import pytest
from pathlib import Path
from src.lexer.scanner import Scanner
from src.parser.parser import Parser
from src.semantic.analyzer import SemanticAnalyzer
from src.ir import IRGenerator, IRPrinter

def collect_tests(subdir):
    base = Path(__file__).parent / 'ir' / subdir
    files = []
    for src_file in sorted(base.glob('*.src')):
        expected_file = src_file.with_suffix('.expected')
        if expected_file.exists():
            files.append((src_file, expected_file))
    return files

@pytest.mark.parametrize("src_file,expected_file", collect_tests("valid"))
def test_ir_valid(src_file, expected_file):
    with open(src_file, 'r', encoding='utf-8-sig') as f:
        source = f.read()
    with open(expected_file, 'r', encoding='utf-8') as f:
        expected = f.read().strip()

    scanner = Scanner(source)
    tokens = []
    while not scanner.is_at_end():
        tokens.append(scanner.next_token())
    tokens.append(scanner.next_token())

    parser = Parser(tokens)
    ast = parser.parse()
    assert len(parser.errors) == 0, f"Syntax errors: {parser.errors}"

    analyzer = SemanticAnalyzer()
    symtable, errors = analyzer.analyze(ast)
    assert len(errors) == 0, f"Semantic errors: {errors}"

    ir_gen = IRGenerator(symtable)
    program_ir = ir_gen.generate(ast)
    printer = IRPrinter()
    output = printer.print_program(program_ir)
    assert output.strip() == expected.strip()

@pytest.mark.parametrize("src_file,expected_file", collect_tests("invalid"))
def test_ir_invalid(src_file, expected_file):
    with open(src_file, 'r', encoding='utf-8-sig') as f:
        source = f.read()
    with open(expected_file, 'r', encoding='utf-8') as f:
        expected_messages = [line.strip() for line in f.read().strip().splitlines() if line.strip()]

    scanner = Scanner(source)
    tokens = []
    while not scanner.is_at_end():
        tokens.append(scanner.next_token())
    tokens.append(scanner.next_token())

    parser = Parser(tokens)
    ast = parser.parse()
    assert len(parser.errors) == 0, f"Syntax errors: {parser.errors}"

    analyzer = SemanticAnalyzer()
    _, errors = analyzer.analyze(ast)
    assert len(errors) > 0, "Expected semantic errors but got none"

    actual_messages = [f"Semantic error: {err.message} at {err.line}:{err.column}" for err in errors]
    assert actual_messages == expected_messages