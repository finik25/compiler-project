import pytest
import sys
from pathlib import Path
from src.lexer.scanner import Scanner
sys.path.insert(0, str(Path(__file__).parent.parent))

TEST_ROOT = Path(__file__).parent / "lexer"


def collect_tests(subdir):
    """Собирает пары (src_file, expected_file) для всех .src файлов в поддиректории."""
    test_dir = TEST_ROOT / subdir
    src_files = sorted(test_dir.glob("*.src"))
    for src_file in src_files:
        expected_file = src_file.with_suffix(".expected")
        if not expected_file.exists():
            pytest.fail(f"Expected file {expected_file} not found for {src_file}")
        yield src_file, expected_file

@pytest.mark.parametrize("src_file,expected_file", list(collect_tests("valid")))
def test_valid(src_file, expected_file):
    run_test(src_file, expected_file)

@pytest.mark.parametrize("src_file,expected_file", list(collect_tests("invalid")))
def test_invalid(src_file, expected_file):
    run_test(src_file, expected_file)

def run_test(src_file, expected_file):
    with open(src_file, "r", encoding="utf-8") as f:
        source = f.read()
    with open(expected_file, "r", encoding="utf-8") as f:
        expected = f.read().strip()

    scanner = Scanner(source)
    output_lines = []
    while not scanner.is_at_end():
        token = scanner.next_token()
        output_lines.append(str(token))
    # Добавляем EOF токен
    output_lines.append(str(scanner.next_token()))
    output = "\n".join(output_lines)

    # Нормализуем пробелы в конце строк
    assert output.rstrip() == expected.rstrip()