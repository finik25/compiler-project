# MiniCompiler

**Учебный проект** по созданию компилятора для упрощённого C-подобного языка.  
Разрабатывается в рамках курса «Построение компиляторов» для изучения этапов трансляции: лексический, синтаксический и семантический анализ, генерация кода.

**Текущий этап (Sprint 1):** Лексический анализатор (сканер) с полной диагностикой ошибок + препроцессор (удаление комментариев) как stretch goal.

## Документация

- [Спецификация языка](docs/language_spec.md) — формальное описание лексем в EBNF.

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

3. **Препроцессор** (опционально):
   - Удаление комментариев с сохранением номеров строк.
   - Запуск только препроцессора:
     ```bash
     compiler preprocess --input examples/hello.src --output cleaned.txt
     ```
   - Лексер с предобработкой:
     ```bash
     compiler lex --input examples/hello.src --preprocess
     ```
   - Просмотр результата препроцессора:
     ```bash
     compiler lex --input examples/hello.src --preprocess --show-preprocessed
     ```

4. **Запуск тестов**:
   ```bash
   python -m pytest tests/ -v
   ```
   Все тесты (22 штуки: 14 для лексера + 8 для препроцессора) должны проходить успешно.

---

## Структура проекта

```
compiler-project/
├── docs/                          # Документация
│   └── language_spec.md            # Спецификация языка
├── examples/                       # Примеры исходного кода
│   └── hello.src
├── src/                            # Исходный код компилятора
│   ├── __init__.py
│   ├── main.py                     # Точка входа CLI
│   ├── lexer/                      # Лексический анализатор
│   │   ├── __init__.py
│   │   ├── scanner.py               # Сканер
│   │   └── token.py                 # Определение токенов
│   ├── preprocessor/                # Препроцессор (stretch goal)
│   │   ├── __init__.py
│   │   └── preprocessor.py
│   └── utils/                       # Вспомогательные модули (будущее)
│       └── __init__.py
├── tests/                           # Тесты
│   ├── __init__.py
│   ├── test_lexer.py                # Тесты лексера (9 тестов)
│   ├── test_preprocessor.py          # Тесты препроцессора (8 тестов)
│   └── preprocessor/                 # Входные файлы для препроцессора
│       ├── valid/                    # Корректные входные файлы
│       │   ├── *.src
│       │   └── *.expected
│       └── invalid/                  # Некорректные входные файлы
│           └── *.src
├── .gitignore
├── generate_expected.py             # Скрипт для перегенерации эталонов
├── README.md
└── setup.py                         # Установка пакета
```

---

## Системные требования

- Python 3.8 или выше
- pip
- (опционально) виртуальное окружение
```
