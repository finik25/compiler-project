# MiniCompiler

Учебный компилятор для упрощённого C-подобного языка.  
Разработан в рамках курса «Построение компиляторов».  
**Текущий этап — Sprint 7:** реализованы указатели, глобальные массивы, поддержка `unsigned int`, короткое замыкание логических операторов, оптимизации IR и вызов внешних функций.  
Все 55 тестов успешно проходят (на целевой платформе Linux).

## Документация

- [Спецификация языка](docs/language_spec.md) — лексика и синтаксис в EBNF.
- [Грамматика языка](src/parser/grammar.md) — полная LL(1)-грамматика.

## Структура проекта

```text
compiler-project/
├── docs/                          # Документация (язык, грамматика)
├── examples/                      # Примеры исходных программ
│   ├── hello.src
│   ├── simple_add.src
│   ├── demo_unsigned.src
│   └── ...
├── src/
│   ├── __init__.py
│   ├── main.py                    # CLI точка входа
│   ├── lexer/                     # Лексический анализатор (Sprint 1)
│   │   ├── scanner.py
│   │   └── token.py
│   ├── preprocessor/              # Препроцессор (удаление комментариев)
│   │   └── preprocessor.py
│   ├── parser/                    # Синтаксический анализатор (Sprint 2)
│   │   ├── __init__.py
│   │   ├── ast.py                 # Узлы AST
│   │   ├── parser.py              # Рекурсивный спуск
│   │   ├── ast_printer.py         # Текстовый вывод AST
│   │   ├── ast_dot.py             # Graphviz DOT для AST
│   │   ├── ast_json.py            # JSON для AST
│   │   └── grammar.md
│   ├── semantic/                  # Семантический анализ (Sprint 3)
│   │   ├── __init__.py
│   │   ├── analyzer.py            # Проверка типов, областей видимости
│   │   ├── symbol_table.py        # Таблица символов
│   │   ├── type_system.py         # Правила совместимости типов
│   │   └── errors.py              # Класс SemanticError
│   ├── ir/                        # Промежуточное представление (Sprint 4)
│   │   ├── __init__.py
│   │   ├── ir_instructions.py     # Классы: Operand, Instruction, BasicBlock
│   │   ├── ir_generator.py        # Генерация IR из AST
│   │   ├── ir_printer.py          # Текстовый вывод IR
│   │   ├── ir_dot.py              # Graphviz для CFG
│   │   ├── ir_json.py             # JSON для IR
│   │   └── optimizer.py           # Оптимизации IR (Sprint 7)
│   └── codegen/                   # Генерация x86-64 кода (Sprint 5-7)
│       ├── __init__.py
│       ├── x86_generator.py       # Основной генератор ассемблера
│       ├── stack_frame.py         # Управление стековыми слотами
│       ├── abi.py                 # Регистры, системные вызовы
│       ├── register_allocator.py  # (экспериментальный) LSRA
│       └── liveness.py            # Анализ живых переменных (для LSRA)
├── tests/                         # Тесты (55 штук)
│   ├── test_lexer.py
│   ├── test_preprocessor.py
│   ├── test_parser.py
│   ├── test_semantic.py
│   ├── test_ir.py
│   ├── test_codegen.py
│   ├── lexer/                     # Входные файлы для лексера
│   ├── preprocessor/              # Входные файлы для препроцессора
│   ├── parser/                    # Входные файлы для парсера
│   ├── semantic/                  # Тесты семантики
│   ├── ir/                        # Тесты IR
│   └── codegen/                   # Тесты кодогенерации
├── .gitignore
├── setup.py
└── README.md
```

## Быстрый старт

### 1. Установка (в виртуальном окружении)

```bash
pip install -e .
```

### 2. Запуск лексера

```bash
compiler lex --input examples/hello.src
```

### 3. Запуск парсера и вывод AST

```bash
compiler parse --input examples/hello.src --format text
compiler parse --input examples/hello.src --format dot --output ast.dot
dot -Tpng ast.dot -o ast.png
```

### 4. Семантический анализ

```bash
compiler check --input examples/valid_ir.src --verbose
```

### 5. Генерация IR

```bash
compiler ir --input examples/valid_ir.src --format text
compiler ir --input examples/valid_ir.src --stats
compiler ir --input tests/ir/valid/if.src --format dot --output cfg.dot
```

### 6. Компиляция в x86-64 ассемблер и запуск

```bash
compiler compile --input examples/simple_add.src --output program.asm
compiler compile --input examples/simple_add.src --run   # требует nasm + ld/gcc
```

### 7. Запуск всех тестов

```bash
pytest tests/ -v
```

## Новые возможности Sprint 7

### Указатели (`&` и `*`)

Поддерживаются взятие адреса переменной, разыменование указателя, присваивание по указателю.

```c
fn main() -> int {
    int x = 42;
    int* p = &x;
    int y = *p;
    return y;   // 42
}
```

### Глобальные массивы

Глобальные массивы размещаются в секциях `.data`/`.bss`, доступ к элементам через индексацию.

```c
int arr[5] = {1,2,3,4,5};
fn main() -> int {
    return arr[2];   // 3
}
```

### `unsigned int` и беззнаковые сравнения

Ключевое слово `unsigned` для целых без знака, корректные сравнения (`ja`/`jb`).

```c
fn main() -> int {
    unsigned int u = 4000000000;
    unsigned int v = 3000000000;
    if (u > v) return 1; else return 0;
}
```

### Короткое замыкание `&&` и `||`

Правый операнд вычисляется только при необходимости.

```c
fn main() -> int {
    int a = 0;
    int b = 10;
    if (a != 0 && b / a > 5) {
        return 0;   // не выполнится
    } else {
        return 1;
    }
}
```

### Оптимизации IR

Флаг `--optimize` включает:
- Constant folding (свёртка констант)
- Constant propagation
- Dead code elimination
- Удаление недостижимых блоков

```bash
compiler compile --input simple_opt.src --output with_opt.asm --optimize
```

### Вызов внешних функций (`extern`)

Поддержка вызова функций из C runtime (printf, malloc, free) с соблюдением System V AMD64 ABI.

```c
extern fn printf(char* fmt, ...);
extern fn malloc(int size) -> int*;
extern fn free(int* ptr) -> void;

fn main() -> int {
    int* p = malloc(4);
    if (p == 0) return 1;
    *p = 42;
    printf("Value: %d\n", *p);
    free(p);
    return 0;
}
```

## Примеры использования

### Компиляция и запуск программы с указателями

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

### Демонстрация сворачивания констант

```bash
cat > const_fold.src << EOF
fn main() -> int {
    return 10 + 20;
}
EOF
compiler compile --input const_fold.src --output no_opt.asm
compiler compile --input const_fold.src --output opt.asm --optimize
diff no_opt.asm opt.asm   # покажет, что в opt.asm сразу mov eax,30
```

## Тестирование

```bash
pytest tests/ -v
```

## Требования к окружению

- Python 3.8+
- NASM (для сборки ассемблера)
- GCC или LD (для линковки)
- Graphviz (опционально, для визуализации)

