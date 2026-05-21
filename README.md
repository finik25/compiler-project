# MiniCompiler

Учебный проект по созданию компилятора для упрощённого C-подобного языка.  
Разрабатывается в рамках курса «Построение компиляторов» для изучения этапов трансляции: лексический, синтаксический и семантический анализ, генерация кода.

**Текущий этап (Sprint 3):** Семантический анализатор, проверка типов, областей видимости, построение символьной таблицы и декорированного AST.

## Документация

- [Спецификация языка](docs/language_spec.md) — формальное описание лексем в EBNF.
- [Грамматика языка](src/parser/grammar.md) — полная LL(1)-грамматика в нотации EBNF.

---

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
   ```
   fn main() {
       int x = 10;
       x++;
       // increment
       return x;
   }
   ```

   Ожидаемый вывод:
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

6. **Семантический анализ** (Sprint 3):
   ```bash
   compiler check --input test_simple.src --verbose
   ```
   Выполняет проверку типов, областей видимости, выводит символьную таблицу, отчёт об ошибках и декорированное AST.
   Поддерживается объявление переменных с выводом типа `var`:
   ```c
   var x = 42;      // тип int
   var y = x + 3;   // тип int
   ```

7. **Запуск тестов**:
   ```bash
   python -m pytest tests/ -v
   ```
   Все тесты (30: лексер, препроцессор, парсер, семантика) должны проходить успешно.

---

## Структура проекта

```
compiler-project/
├── docs/                          # Документация
│   └── language_spec.md
├── examples/                      # Примеры исходного кода
│   └── hello.src
├── src/                           # Исходный код
│   ├── __init__.py
│   ├── main.py                    # CLI
│   ├── lexer/                     # Лексический анализатор
│   │   ├── scanner.py
│   │   └── token.py
│   ├── preprocessor/              # Препроцессор (stretch goal)
│   │   └── preprocessor.py
│   ├── parser/                    # Синтаксический анализатор
│   │   ├── __init__.py
│   │   ├── ast.py                 # Узлы AST
│   │   ├── parser.py              # Рекурсивный спуск
│   │   ├── ast_printer.py         # Текстовый вывод AST
│   │   ├── ast_dot.py             # Генератор DOT
│   │   ├── ast_json.py            # Генератор JSON
│   │   └── grammar.md             # Формальная грамматика
│   ├── semantic/                  # Семантический анализ (Sprint 3)
│   │   ├── __init__.py
│   │   ├── analyzer.py            # Visitor и проверки
│   │   ├── symbol_table.py        # Таблица символов и области
│   │   ├── type_system.py         # Совместимость типов
│   │   └── errors.py              # Класс SemanticError
│   └── utils/                     # Вспомогательные модули (будущее)
├── tests/                         # Тесты
│   ├── test_lexer.py
│   ├── test_preprocessor.py
│   ├── test_parser.py
│   ├── test_semantic.py
│   ├── lexer/                     # Входные файлы для лексера
│   ├── preprocessor/              # Входные файлы для препроцессора
│   ├── parser/                    # Входные файлы для парсера
│   └── semantic/                  # Тесты семантики (valid/invalid)
├── .gitignore
├── generate_expected.py           # Генерация эталонов для лексера/препроцессора
├── generate_parser_expected.py    # Генерация эталонов для парсера
├── generate_semantic_expected.py  # Генерация эталонов для семантики
├── README.md
└── setup.py
```

---

## Системные требования

- Python 3.8 или выше
- pip
- (опционально) Graphviz для визуализации AST
- (опционально) виртуальное окружение
