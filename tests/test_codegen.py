import subprocess
import tempfile
from pathlib import Path

CODEGEN_VALID = Path(__file__).parent / "codegen" / "valid"

def run_codegen_test(src_path: Path, expected_file: Path):
    expected = expected_file.read_text().strip()
    if "print" in src_path.name:
        # Отдельная сборка и запуск для тестов вывода
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".asm", delete=False) as asm_file:
            asm_path = asm_file.name
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".exe", delete=False) as exe_path:
            exe_file = exe_path.name
        obj_path = exe_file.replace(".exe", ".o")
        # 1. Генерация ассемблера
        subprocess.run(["compiler", "compile", "--input", str(src_path), "--output", asm_path], check=True)
        # 2. Ассемблирование
        subprocess.run(["nasm", "-f", "elf64", asm_path, "-o", obj_path], check=True)
        # 3. Линковка
        subprocess.run(["ld", "-o", exe_file, obj_path], check=True)
        # 4. Запуск с перенаправлением вывода в файл
        out_file = exe_file + ".out"
        subprocess.run([exe_file], stdout=open(out_file, "w"), stderr=subprocess.PIPE)
        # 5. Чтение вывода
        with open(out_file, "r") as f:
            output = f.read().strip()
        # 6. Проверка
        assert expected in output, f"Expected '{expected}' in output, got '{output}'"
        # 7. Очистка
        for p in [asm_path, obj_path, exe_file, out_file]:
            Path(p).unlink(missing_ok=True)
    else:
        # Для тестов на код возврата
        cmd = ["compiler", "compile", "--input", str(src_path), "--run"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == int(expected), \
            f"Exit code mismatch: expected {expected}, got {result.returncode}\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"

def test_arith():
    run_codegen_test(CODEGEN_VALID / "test_arith.src", CODEGEN_VALID / "test_arith.expected")

def test_if():
    run_codegen_test(CODEGEN_VALID / "test_if.src", CODEGEN_VALID / "test_if.expected")

def test_while():
    run_codegen_test(CODEGEN_VALID / "test_while.src", CODEGEN_VALID / "test_while.expected")

def test_global():
    run_codegen_test(CODEGEN_VALID / "test_global.src", CODEGEN_VALID / "test_global.expected")

def test_short_circuit_and():
    run_codegen_test(CODEGEN_VALID / "test_short_circuit_and.src", CODEGEN_VALID / "test_short_circuit_and.expected")

def test_short_circuit_or():
    run_codegen_test(CODEGEN_VALID / "test_short_circuit_or.src", CODEGEN_VALID / "test_short_circuit_or.expected")

def test_unsigned():
    run_codegen_test(CODEGEN_VALID / "test_unsigned.src", CODEGEN_VALID / "test_unsigned.expected")
'''
def test_short_circuit_simple():
    run_codegen_test(CODEGEN_VALID / "test_short_circuit_simple.src", CODEGEN_VALID / "test_short_circuit_simple.expected")

def test_print():
    run_codegen_test(CODEGEN_VALID / "test_print.src", CODEGEN_VALID / "test_print.expected")'''