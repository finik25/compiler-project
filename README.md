
# MiniCompiler

Учебный компилятор для упрощённого C-подобного языка.  
Разработан в рамках курса «Построение компиляторов».  
**Текущий этап — Sprint 6:** реализованы прямые условные переходы, поддержка `unsigned int`, короткое замыкание логических операторов, глобальные переменные.  
Все 49 тестов успешно проходят.

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
│   │   └── ir_json.py             # JSON для IR
│   └── codegen/                   # Генерация x86-64 кода (Sprint 5-6)
│       ├── __init__.py
│       ├── x86_generator.py       # Основной генератор ассемблера
│       ├── stack_frame.py         # Управление стековыми слотами
│       ├── abi.py                 # Регистры, системные вызовы
│       ├── register_allocator.py  # (экспериментальный) LSRA
│       └── liveness.py            # Анализ живых переменных (для LSRA)
├── tests/                         # Тесты (49 штук)
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
compiler compile --input examples/simple_add.src --run   # требует nasm + ld
```

### 7. Запуск всех тестов

```bash
pytest tests/ -v
```

## Промежуточное представление (IR)

IR — трёхадресный код с базовыми блоками. Инструкции:
- Арифметика: `ADD`, `SUB`, `MUL`, `DIV`, `MOD`
- Логика: `AND`, `OR`, `NOT`, `XOR`
- Сравнения: `CMP_EQ`, `CMP_NE`, `CMP_LT`, `CMP_LE`, `CMP_GT`, `CMP_GE`
- Прямые условные переходы: `BR_EQ`, `BR_NE`, `BR_LT`, `BR_LE`, `BR_GT`, `BR_GE`, `BR_ULT`, `BR_ULE`, `BR_UGT`, `BR_UGE`
- Управление: `JUMP`, `JUMP_IF`, `JUMP_IF_NOT`, `LABEL`
- Функции: `CALL`, `RETURN`, `PARAM`
- Данные: `MOVE`, `LOAD`, `STORE`

Пример IR для функции `factorial`:
```text
function factorial: int (int n)
  entry:
    t1 = CMP_LE n, 1
    JUMP_IF t1, L_true
    JUMP L_false
  L_true:
    RETURN 1
  L_false:
    t2 = SUB n, 1
    PARAM 0, t2
    t3 = CALL factorial, 1
    t4 = MUL n, t3
    RETURN t4
```

## Генерация x86-64 кода (Sprint 5-6)

Кодогенератор преобразует IR в ассемблер NASM для x86-64, следуя **System V AMD64 ABI**.  
По умолчанию используется **стековая модель** (все временные переменные хранятся на стеке). Это надёжно и достаточно для демонстрации всех возможностей языка. Экспериментальный регистровый аллокатор (LSRA) присутствует в исходном коде, но отключён из-за нестабильности.

### Прямые условные переходы

Для реляционных операторов генерируются прямые `cmp` + условный переход, без лишних `setcc`/`movzx`.  
Поддерживаются как знаковые, так и беззнаковые переходы (`jl`/`jb`, `jg`/`ja` и т.д.).

**Пример для `if (x < y)`**:
```asm
    mov rax, [rbp-8]
    mov rbx, [rbp-16]
    cmp rax, rbx
    jl .then
    jmp .else
.then:
    ...
.else:
    ...
```

### Поддержка `unsigned int`

- Лексер распознаёт ключевое слово `unsigned`.
- Парсер формирует тип `"unsigned int"`.
- Семантический анализ допускает неявное приведение `int` → `unsigned int`.
- IR содержит флаг `is_unsigned` для выбора правильных арифметических и сравнительных инструкций.
- Кодогенератор использует беззнаковые инструкции `mul`/`div` и переходы `jb`/`ja`/`jbe`/`jae`.

**Пример (`demo_unsigned.src`):**
```c
unsigned int u = 4000000000;
unsigned int v = 3000000000;
if (u > v) return 1; else return 0;
```

Сгенерированный фрагмент:
```asm
    mov rax, 4000000000
    mov [rbp-8], rax
    mov rax, 3000000000
    mov [rbp-16], rax
    cmp rax, rbx
    ja .then1        # беззнаковое "выше"
    jmp .else2
```

### Короткое замыкание `&&` и `||`

Логические операторы транслируются в цепочки условных переходов. Правый операнд вычисляется только при необходимости. Протестировано на выражениях без побочных эффектов (тесты `test_short_circuit_and` и `test_short_circuit_or` проходят).

### Глобальные переменные

Глобальные переменные размещаются в секциях `.data` (инициализированные) или `.bss` (неинициализированные). Доступ через `rel`-адресацию. Поддерживаются типы `int`, `unsigned int`, `bool`.

## Проверка сгенерированного ассемблера

После компиляции можно проанализировать выходной файл:

```bash
compiler compile --input examples/demo_unsigned.src --output test.asm
cat test.asm | grep -E "ja|jb|jl|jg"
```

Ожидаемый вывод для `demo_unsigned.src`:
```asm
    ja .then1
```

Также можно собрать и запустить исполняемый файл:

```bash
compiler compile --input examples/demo_unsigned.src --run
echo $LASTEXITCODE   # в PowerShell: $LASTEXITCODE, в bash: echo $?
```

Код возврата должен быть `1`, так как 4000000000 > 3000000000.

## Тестирование

Все 49 тестов проходят. Запуск:

```bash
pytest tests/ -v
```

Результат:
```
====================== 49 passed in 1.80s ======================
```

Категории тестов:
- Лексика (valid / invalid)
- Препроцессор
- Синтаксис (valid / invalid)
- Семантика (valid / invalid)
- IR (валидные программы и ожидаемые ошибки)
- Кодогенерация (арифметика, if, while, глобальные переменные, short-circuit, unsigned)

## Системные требования

- **Python 3.8+**
- **pip**
- **Graphviz** (опционально, для визуализации AST и CFG)
- **NASM** и **GNU ld** (опционально, для сборки и запуска сгенерированного кода)

## Что нового в Sprint 6

| Возможность | Статус |
|-------------|--------|
| Прямые условные переходы (`jl`, `jg`, `je`, `jne`, `jb`, `ja` и т.д.) | ✅ Реализованы |
| Поддержка `unsigned int` (все этапы) | ✅ Полностью |
| Короткое замыкание `&&` / `||` (без побочных эффектов) | ✅ Проходит тесты |
| Глобальные переменные (включая `unsigned int`) | ✅ Работают |
| Регистровая аллокация (локальная) | ⚠️ Отключена (LSRA в коде, но нестабилен) |
| Short-circuit с вызовом функции | ⚠️ Отложен (не влияет на основную функциональность) |

## Планы на Sprint 7

- Стабилизация локальной регистровой аллокации.
- Поддержка динамических массивов (куча) через `malloc`/`free`.
- Оптимизации: постоянное сворачивание, удаление мёртвого кода.
- `break` и `continue` в циклах.
