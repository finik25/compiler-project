import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.lexer.scanner import Scanner
from src.parser.parser import Parser
from src.parser.ast_printer import ASTPrinter

TEST_ROOT = Path(__file__).parent / "parser"


def collect_tests(subdir):
    test_dir = TEST_ROOT / subdir
    src_files = sorted(test_dir.glob("*.src"))
    for src_file in src_files:
        expected_file = src_file.with_suffix(".expected")
        if not expected_file.exists():
            if subdir == "valid":
                pytest.fail(f"Expected file {expected_file} not found for {src_file}")
            else:
                yield src_file, None
        else:
            yield src_file, expected_file


@pytest.mark.parametrize("src_file,expected_file", list(collect_tests("valid")))
def test_parser_valid(src_file, expected_file):
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
    printer = ASTPrinter()
    output = printer.print_text(ast)

    assert len(parser.errors) == 0, f"Unexpected errors: {parser.errors}"
    assert output.strip() == expected.strip()


@pytest.mark.parametrize("src_file,_", list(collect_tests("invalid")))
def test_parser_invalid(src_file, _):
    with open(src_file, 'r', encoding='utf-8-sig') as f:
        source = f.read()
    scanner = Scanner(source)
    tokens = []
    while not scanner.is_at_end():
        tokens.append(scanner.next_token())
    tokens.append(scanner.next_token())

    parser = Parser(tokens)
    ast = parser.parse()
    # Ожидаем хотя бы одну ошибку
    assert len(parser.errors) > 0, f"Expected errors but got none for {src_file}"