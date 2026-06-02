## План демонстрации Sprint 8 на Ubuntu

### 1. Подготовка системы (установка необходимых пакетов)
Если на чистой Ubuntu чего-то не хватает:
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nasm gcc git
```

### 2. Клонирование репозитория
```bash
git clone https://github.com/finik25/compiler-project
cd compiler-project
```

### 3. Создание и активация виртуального окружения
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Установка компилятора в режиме разработки
```bash
pip install -e .
```
Теперь команда `compiler` доступна.

### 5. Установка pytest (если не установлен)
```bash
pip install pytest
```

### 6. Запуск всех тестов (55 должны пройти)
```bash
pytest tests/ -v
```

### 7. Демонстрация с помощью скрипта `run_demo.sh`
Сделайте скрипт исполняемым и запустите:
```bash
chmod +x run_demo.sh
./run_demo.sh
```
Ожидаемый вывод:
```
Exit code: 89
SUCCESS
```

### 8. Дополнительные точечные проверки (по желанию преподавателя)

#### Глобальные массивы (тест из набора)
```bash
compiler compile --input tests/codegen/valid/global_array.src --run
echo $?   # 30
```

#### Указатели
```bash
cat > test_ptr.src << EOF
fn main() -> int {
    int x = 42;
    int* p = &x;
    return *p;
}
EOF
compiler compile --input test_ptr.src --run
echo $?   # 42
```

#### Оптимизация (сворачивание констант)
```bash
cat > test_opt.src << EOF
fn main() -> int {
    return 10 + 20;
}
EOF
compiler compile --input test_opt.src --output test_opt.asm --optimize
grep -q "mov.*30" test_opt.asm && echo "Constant folding OK" || echo "Constant folding FAILED"
```

#### unsigned int и короткое замыкание
```bash
cat > test_unsigned.src << EOF
fn main() -> int {
    unsigned int u = 4000000000;
    unsigned int v = 3000000000;
    if (u > v) return 1; else return 0;
}
EOF
compiler compile --input test_unsigned.src --run
echo $?   # 1
```

### 9. Очистка (опционально)
```bash
deactivate
cd ..
rm -rf compiler-project
```

---
