#!/bin/bash
# Скрипт для компиляции, сборки и запуска демонстрационной программы

set -e  # остановка при ошибке

SOURCE="demo8.src"
ASM="demo8.asm"
OBJ="demo8.o"
EXE="demo8"

echo "=== Компиляция MiniCompiler ==="
compiler compile --input "$SOURCE" --output "$ASM" --optimize

echo "=== Ассемблирование NASM ==="
nasm -f elf64 "$ASM" -o "$OBJ"

echo "=== Линковка (gcc) ==="
gcc -no-pie -o "$EXE" "$OBJ"

echo "=== Запуск программы ==="
./"$EXE"
EXIT_CODE=$?
echo "Код возврата: $EXIT_CODE"

# Проверка ожидаемого значения
if [ $EXIT_CODE -eq 89 ]; then
    echo "✅ Демонстрация успешна: получен ожидаемый код 89"
else
    echo "❌ Ошибка: ожидалось 89, получено $EXIT_CODE"
    exit 1
fi