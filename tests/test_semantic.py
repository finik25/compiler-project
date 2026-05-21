import pytest
from pathlib import Path
from src.lexer.scanner import Scanner
from src.parser.parser import Parser
from src.semantic.analyzer import SemanticAnalyzer

def collect_tests(subdir):
    base = Path(__file__).parent / 'semantic' / subdir
    files = []
    for src_file in sorted(base.glob('*.src')):
        expected_file = src_file.with_suffix('.expected')
        files.append((src_file, expected_file))
    return files

@pytest.mark.parametrize("src_file,expected_file", collect_tests("valid"))
def test_semantic_valid(src_file, expected_file):
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

    output_lines = []
    if errors:
        for err in errors:
            output_lines.append(f"Semantic error: {err.message} at {err.line}:{err.column}")
    else:
        output_lines.append("Semantic analysis passed")
        output_lines.append("")
        output_lines.append("Symbol Table:")
        output_lines.append(symtable.dump())

    output = "\n".join(output_lines)
    assert output == expected

@pytest.mark.parametrize("src_file,expected_file", collect_tests("invalid"))
def test_semantic_invalid(src_file, expected_file):
    # Для негативных тестов expected_file содержит ожидаемые ошибки (несколько строк)
    with open(src_file, 'r', encoding='utf-8-sig') as f:
        source = f.read()
    with open(expected_file, 'r', encoding='utf-8') as f:
        expected_errors = [line.strip() for line in f.readlines() if line.strip()]

    scanner = Scanner(source)
    tokens = []
    while not scanner.is_at_end():
        tokens.append(scanner.next_token())
    tokens.append(scanner.next_token())

    parser = Parser(tokens)
    ast = parser.parse()
    # может быть синтаксическая ошибка, тогда тест должен упасть, но для семантических ошибок синтаксис правильный
    # предполагаем, что синтаксис верен, иначе тест невалиден
    assert len(parser.errors) == 0, f"Syntax errors: {parser.errors}"

    analyzer = SemanticAnalyzer()
    _, errors = analyzer.analyze(ast)

    actual_messages = [f"Semantic error: {err.message} at {err.line}:{err.column}" for err in errors]
    assert actual_messages == expected_errors