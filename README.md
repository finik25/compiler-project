
# MiniCompiler

Учебный проект по созданию компилятора для упрощённого C-подобного языка.  
Разрабатывается в рамках курса «Построение компиляторов» для изучения этапов трансляции: лексический, синтаксический, семантический анализ, генерация промежуточного кода (IR) и машинного кода.

**Текущий этап (Sprint 4):** Генерация промежуточного представления (трёхадресный код, базовые блоки, CFG), вывод в текстовом, JSON и Graphviz форматах, статистика IR.

## Документация

- [Спецификация языка](docs/language_spec.md) — формальное описание лексем в EBNF.
- [Грамматика языка](src/parser/grammar.md) — полная LL(1)-грамматика в нотации EBNF.

## Быстрый старт (Quick Start)

1. **Установка в режиме разработки** (рекомендуется виртуальное окружение):
   ```bash
   pip install -e .
   ```

2. **Запуск лексера на примере**:
   ```bash
   compiler lex --input examples/hello.src
   ```

   Пример файла `examples/hello.src`:
   ```c
   fn main() {
       int x = 10;
       x++;
       // increment
       return x;
   }
   ```

   Ожидаемый вывод токенов:
   ```
   1:1 KW_FN "fn"
   1:4 IDENTIFIER "main"
   1:8 LPAREN "("
   1:9 RPAREN ")"
   1:10 LBRACE "{"
   2:5 KW_INT "int"
   2:9 IDENTIFIER "x"
   2:11 ASSIGN "="
   2:13 INT_LITERAL "10" 10
   2:15 SEMICOLON ";"
   3:5 IDENTIFIER "x"
   3:6 INC_OP "++"
   3:8 SEMICOLON ";"
   4:5 KW_RETURN "return"
   4:12 IDENTIFIER "x"
   4:13 SEMICOLON ";"
   5:1 RBRACE "}"
   6:1 END_OF_FILE ""
   ```

3. **Запуск парсера с выводом AST**:
   ```bash
   compiler parse --input examples/hello.src --format text
   ```
   Поддерживаются форматы: `text`, `dot` (Graphviz), `json`.

4. **Генерация графа AST** (требуется Graphviz):
   ```bash
   compiler parse --input examples/hello.src --format dot --output ast.dot
   dot -Tpng ast.dot -o ast.png
   ```

5. **Препроцессор** (удаление комментариев):
   ```bash
   compiler preprocess --input examples/hello.src --output cleaned.txt
   compiler lex --input examples/hello.src --preprocess
   ```

6. **Семантический анализ**:
   ```bash
   compiler check --input test_simple.src --verbose
   ```
   Выполняет проверку типов, областей видимости, выводит символьную таблицу, отчёт об ошибках и декорированное AST. Поддерживается объявление переменных с выводом типа `var`:
   ```c
   var x = 42;      // тип int
   var y = x + 3;   // тип int
   ```

7. **Генерация промежуточного кода (IR)** (Sprint 4):
   ```bash
   # Текстовый вывод IR
   compiler ir --input examples/valid_ir.src --format text

   # С подробной информацией (локальные переменные)
   compiler ir --input examples/valid_ir.src --verbose

   # Сохранить в файл
   compiler ir --input examples/valid_ir.src --output program.ir

   # Статистика IR
   compiler ir --input examples/valid_ir.src --stats

   # Граф потока управления (CFG) в Graphviz
   compiler ir --input tests/ir/valid/nested_if.src --format dot --output nested_if.dot
   dot -Tpng nested_if.dot -o nested_if_new.png

   # JSON вывод
   compiler ir --input examples/valid_ir.src --format json
   ```

8. **Запуск тестов**:
   ```bash
   python -m pytest tests/ -v
   ```
   Все тесты (лексика, препроцессор, синтаксис, семантика, IR) должны проходить успешно.

## Структура проекта

```
compiler-project/
├── docs/                          # Документация
│   └── language_spec.md
├── examples/                      # Примеры исходного кода
│   ├── hello.src
│   └── valid_ir.src
├── src/                           # Исходный код
│   ├── __init__.py
│   ├── main.py                    # CLI
│   ├── lexer/                     # Лексический анализатор (Sprint 1)
│   │   ├── scanner.py
│   │   └── token.py
│   ├── preprocessor/              # Препроцессор (stretch goal)
│   │   └── preprocessor.py
│   ├── parser/                    # Синтаксический анализатор (Sprint 2)
│   │   ├── __init__.py
│   │   ├── ast.py                 # Узлы AST
│   │   ├── parser.py              # Рекурсивный спуск
│   │   ├── ast_printer.py         # Текстовый вывод AST
│   │   ├── ast_dot.py             # Генератор DOT для AST
│   │   ├── ast_json.py            # Генератор JSON для AST
│   │   └── grammar.md             # Формальная грамматика
│   ├── semantic/                  # Семантический анализ (Sprint 3)
│   │   ├── __init__.py
│   │   ├── analyzer.py            # Visitor и проверки
│   │   ├── symbol_table.py        # Таблица символов и области
│   │   ├── type_system.py         # Совместимость типов
│   │   └── errors.py              # Класс SemanticError
│   ├── ir/                        # Промежуточное представление (Sprint 4)
│   │   ├── __init__.py
│   │   ├── ir_instructions.py     # Классы Operand, Instruction, BasicBlock и др.
│   │   ├── ir_generator.py        # Генератор IR из декорированного AST
│   │   ├── ir_printer.py          # Текстовый вывод IR (с поддержкой --verbose)
│   │   ├── ir_dot.py              # Генератор CFG в Graphviz DOT
│   │   └── ir_json.py             # Генератор JSON для IR
│   └── utils/                     # Вспомогательные модули (будущее)
├── tests/                         # Тесты
│   ├── test_lexer.py
│   ├── test_preprocessor.py
│   ├── test_parser.py
│   ├── test_semantic.py
│   ├── test_ir.py
│   ├── lexer/                     # Входные файлы для лексера
│   ├── preprocessor/              # Входные файлы для препроцессора
│   ├── parser/                    # Входные файлы для парсера
│   ├── semantic/                  # Тесты семантики (valid/invalid)
│   └── ir/                        # Тесты IR (valid)
├── .gitignore
├── generate_expected.py           # Генерация эталонов для лексера/препроцессора
├── generate_parser_expected.py    # Генерация эталонов для парсера
├── generate_semantic_expected.py  # Генерация эталонов для семантики
├── README.md
└── setup.py
```

## Промежуточное представление (IR)

IR — это трёхадресный код с базовыми блоками, который служит мостом между AST и генерацией машинного кода. Каждая инструкция имеет не более трёх операндов (`dest = src1 op src2` или `dest = op src1`). Управляющие инструкции (`JUMP`, `JUMP_IF`, `JUMP_IF_NOT`, `RETURN`) разделяют базовые блоки.

### Пример генерации IR

Исходный код (`examples/valid_ir.src`):
```c
fn main() -> int {
    int x = 10;
    int y = 20;
    int z = x + y;
    return z;
}
```

Текстовый вывод IR:
```
function main: int ()
  entry:
    t1 = MOVE 10
    t2 = MOVE 20
    t3 = ADD t1, t2
    RETURN t3
```

С флагом `--verbose` добавляется секция `locals:`, показывающая соответствие исходных переменных типам:
```
function main: int ()
  locals:
    x: int
    y: int
    z: int
  entry:
    t1 = MOVE 10
    t2 = MOVE 20
    t3 = ADD t1, t2
    RETURN t3
```

### Формат JSON

```bash
compiler ir --input examples/valid_ir.src --format json
```
Выдаёт структурированное представление IR, пригодное для машинной обработки.

### Статистика IR

```bash
compiler ir --input examples/valid_ir.src --stats
```
Выводит количество функций, базовых блоков, инструкций и временных переменных.

### Визуализация графа потока управления (CFG)

```bash
compiler ir --input tests/ir/valid/nested_if.src --format dot --output nested_if.dot

dot -Tpng nested_if.dot -o nested_if_new.png
```

CFG показывает базовые блоки и переходы между ними.

## Системные требования

- Python 3.8 или выше
- pip
- (опционально) Graphviz для визуализации AST и CFG
- (опционально) виртуальное окружение

