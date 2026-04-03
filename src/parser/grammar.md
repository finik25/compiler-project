# Грамматика языка MiniCompiler

## 1. Введение

Данный документ описывает контекстно-свободную грамматику (КС-грамматику) языка MiniCompiler в нотации EBNF. Грамматика предназначена для построения **LL(1)** рекурсивного парсера.

Грамматика основана на лексических токенах, определённых в [language_spec.md](../../docs/language_spec.md). Все терминальные символы (токены) записаны в верхнем регистре и соответствуют типам `TokenType` из лексического анализатора.

## 2. Нотация EBNF

В описании используются следующие метасимволы:

| Символ | Значение |
|--------|----------|
| `::=`  | Определение нетерминала |
| `\|`   | Альтернатива |
| `{ ... }` | Повторение (0 или более раз) |
| `[ ... ]` | Необязательная конструкция |
| `(...)` | Группировка |
| `"терминал"` | Терминальный символ (токен) |

Имена терминалов совпадают с именами в `TokenType` (например, `KW_INT`, `IDENTIFIER`, `PLUS`).

## 3. Терминальные символы (токены)

Грамматика использует следующие терминалы (полный список см. в `src/lexer/token.py`):

**Ключевые слова:**
`KW_IF`, `KW_ELSE`, `KW_WHILE`, `KW_FOR`, `KW_INT`, `KW_FLOAT`, `KW_BOOL`, `KW_RETURN`, `KW_TRUE`, `KW_FALSE`, `KW_VOID`, `KW_STRUCT`, `KW_FN`

**Идентификаторы и литералы:**
`IDENTIFIER`, `INT_LITERAL`, `FLOAT_LITERAL`, `STRING_LITERAL`

**Операторы:**
`PLUS`, `MINUS`, `STAR`, `SLASH`, `PERCENT`, `ASSIGN`, `EQ`, `NE`, `LT`, `LE`, `GT`, `GE`, `AND`, `OR`, `NOT`, `INC_OP`, `DEC_OP`, `ADD_ASSIGN`, `SUB_ASSIGN`, `MUL_ASSIGN`, `DIV_ASSIGN`

**Разделители:**
`LPAREN`, `RPAREN`, `LBRACE`, `RBRACE`, `LBRACKET`, `RBRACKET`, `SEMICOLON`, `COMMA`, `COLON`, `ARROW` (→)

## 4. Грамматические правила

### 4.1. Программа
```
Program ::= { Declaration }
```

### 4.2. Объявления
```
Declaration ::= FunctionDecl
              | StructDecl
              | VarDecl
              | Statement

FunctionDecl ::= KW_FN IDENTIFIER LPAREN [ Parameters ] RPAREN [ ARROW Type ] Block

StructDecl ::= KW_STRUCT IDENTIFIER LBRACE { VarDecl } RBRACE

VarDecl ::= Type IDENTIFIER [ ASSIGN Expression ] SEMICOLON

Type ::= KW_INT
       | KW_FLOAT
       | KW_BOOL
       | KW_VOID
       | KW_STRUCT IDENTIFIER

Parameters ::= Parameter { COMMA Parameter }
Parameter ::= Type IDENTIFIER
```

### 4.3. Операторы
```
Statement ::= Block
            | IfStmt
            | WhileStmt
            | ForStmt
            | ReturnStmt
            | ExprStmt
            | EmptyStmt

Block ::= LBRACE { Statement } RBRACE

IfStmt ::= KW_IF LPAREN Expression RPAREN Statement [ KW_ELSE Statement ]

WhileStmt ::= KW_WHILE LPAREN Expression RPAREN Statement

ForStmt ::= KW_FOR LPAREN [ ForInit ] SEMICOLON [ Expression ] SEMICOLON [ Expression ] RPAREN Statement

ForInit ::= VarDecl | Expression

ReturnStmt ::= KW_RETURN [ Expression ] SEMICOLON

ExprStmt ::= Expression SEMICOLON

EmptyStmt ::= SEMICOLON
```

### 4.4. Выражения (с приоритетами, без левой рекурсии)
```
Expression ::= Assignment

Assignment ::= LogicalOr [ ( ASSIGN | ADD_ASSIGN | SUB_ASSIGN | MUL_ASSIGN | DIV_ASSIGN ) Assignment ]

LogicalOr ::= LogicalAnd { OR LogicalAnd }

LogicalAnd ::= Equality { AND Equality }

Equality ::= Relational { ( EQ | NE ) Relational }

Relational ::= Additive { ( LT | LE | GT | GE ) Additive }

Additive ::= Multiplicative { ( PLUS | MINUS ) Multiplicative }

Multiplicative ::= Unary { ( STAR | SLASH | PERCENT ) Unary }

Unary ::= ( MINUS | NOT | INC_OP | DEC_OP ) Unary
        | Postfix

Postfix ::= Call { INC_OP | DEC_OP }

Call ::= Primary { LPAREN [ Arguments ] RPAREN }

Primary ::= Literal
          | IDENTIFIER
          | LPAREN Expression RPAREN

Literal ::= INT_LITERAL
          | FLOAT_LITERAL
          | STRING_LITERAL
          | KW_TRUE
          | KW_FALSE

Arguments ::= Expression { COMMA Expression }
```

## 5. LL(1)-свойства и разрешение конфликтов

### 5.1. Устранение левой рекурсии
В исходной грамматике существовала левая рекурсия в правилах для выражений (например, `Additive ::= Additive "+" Multiplicative`). В приведённой версии левая рекурсия заменена на итерации с использованием `{ ... }`, что эквивалентно правой рекурсии и позволяет реализовать парсер без рекурсивных вызовов (через циклы).

### 5.2. FIRST-множества
Ключевые FIRST-множества нетерминалов:

| Нетерминал | FIRST |
|------------|-------|
| `Declaration` | `{ KW_FN, KW_STRUCT, KW_INT, KW_FLOAT, KW_BOOL, KW_VOID, LBRACE, KW_IF, KW_WHILE, KW_FOR, KW_RETURN, IDENTIFIER, LPAREN, INT_LITERAL, ... }` |
| `Statement` | `{ LBRACE, KW_IF, KW_WHILE, KW_FOR, KW_RETURN, IDENTIFIER, LPAREN, INT_LITERAL, ... }` |
| `VarDecl` | `{ KW_INT, KW_FLOAT, KW_BOOL, KW_VOID, KW_STRUCT }` |
| `Expression` | `{ IDENTIFIER, LPAREN, INT_LITERAL, FLOAT_LITERAL, STRING_LITERAL, KW_TRUE, KW_FALSE, MINUS, NOT, INC_OP, DEC_OP }` |
| `Type` | `{ KW_INT, KW_FLOAT, KW_BOOL, KW_VOID, KW_STRUCT }` |
| `Unary` | `{ MINUS, NOT, INC_OP, DEC_OP, IDENTIFIER, LPAREN, INT_LITERAL, ... }` |

### 5.3. Конфликт `KW_STRUCT` в `Declaration`
Правила `StructDecl` и `VarDecl` (где `Type` может начинаться с `KW_STRUCT`) имеют общий префикс `KW_STRUCT`. Это единственное место, где требуется более одного токена предпросмотра.

**Разрешение:**  
В парсере при встрече `KW_STRUCT` запоминается позиция и проверяется следующий токен:
- Если следующий токен — `IDENTIFIER`, и за ним идёт `LBRACE` → разбираем `StructDecl`.
- В противном случае → откатываемся и разбираем `VarDecl` (с `KW_STRUCT IDENTIFIER` как тип).

Такое решение требует 2-токенного предпросмотра, что допустимо в рекурсивном спуске и не нарушает LL(1) для остальных правил.

### 5.4. Конфликт `ForInit`
`ForInit ::= VarDecl | Expression`. FIRST(VarDecl) = `{ KW_INT, KW_FLOAT, KW_BOOL, KW_VOID, KW_STRUCT }`, FIRST(Expression) = `{ IDENTIFIER, LPAREN, INT_LITERAL, ... }`. Множества не пересекаются, конфликта нет.

### 5.5. Проблема "dangling else"
Правило `IfStmt ::= KW_IF ... Statement [ KW_ELSE Statement ]` приводит к классической неоднозначности: `else` может принадлежать как ближайшему, так и внешнему `if`. В LL(1) это разрешается путём предпочтения ближайшего `else`. Реализация: после разбора `then`-ветви сразу проверяем наличие `else`. Таким образом, `else` всегда связывается с самым внутренним `if`.

## 6. Приоритеты и ассоциативность операторов

| Уровень | Операторы | Ассоциативность |
|---------|-----------|-----------------|
| 11 | `= += -= *= /=` | Правая |
| 10 | `\|\|` | Левая |
| 9 | `&&` | Левая |
| 8 | `== !=` | Неассоциативна |
| 7 | `< <= > >=` | Неассоциативна |
| 6 | `+ -` | Левая |
| 5 | `* / %` | Левая |
| 4 | `- ! ++ --` (унарные) | Правая |
| 3 | `++ --` (постфиксные) | Левая |
| 2 | `()` (вызов) | Левая |
| 1 | литералы, идентификаторы, `()` | – |

Приоритеты реализованы через иерархию нетерминалов: `Assignment` (низший) → `LogicalOr` → ... → `Primary` (высший).

## 7. Особенности реализации

### 7.1. Префиксные и постфиксные `++` и `--`
- Префиксные: обрабатываются в правиле `Unary` как часть унарных операторов.
- Постфиксные: обрабатываются в `Postfix` после разбора `Call`. Допустимо применение нескольких постфиксных операторов (например, `x++--`), хотя семантически это редко имеет смысл. Парсер может ограничиться одним.

### 7.2. Присваивание
Правило `Assignment` праворекурсивно, что даёт правую ассоциативность: `a = b = c` разбирается как `a = (b = c)`. Левая часть присваивания должна быть идентификатором; это проверяется при построении AST.

### 7.3. Вызовы функций
Вызовы (`Call`) могут быть цепочками: `foo()()` не допускается в языке, но грамматика позволяет, так как `Call` включает `Primary { LPAREN ... }`. Парсер должен проверить, что после вызова `foo()` следующий вызов может применяться только к результату, возвращающему функцию. В нашем языке функции не могут возвращать функции, поэтому цепочки вызовов запрещены; это будет проверяться семантически.

### 7.4. Обработка ошибок
При возникновении синтаксической ошибки парсер должен сообщить о ней с указанием строки и колонки, а затем попытаться восстановиться, пропуская токены до ближайшего синхронизирующего маркера (например, `SEMICOLON`, `RBRACE` или начало нового оператора/объявления).

## 8. Примеры разбора

### 8.1. Пример программы
```
fn main() -> int {
    int x = 10;
    if (x > 5) {
        return x;
    } else {
        return 0;
    }
}
```

### 8.2. Разбор выражения `a + b * c`
```
Expression → Assignment → LogicalOr → LogicalAnd → Equality → Relational → Additive
Additive → Multiplicative { PLUS Multiplicative }
Multiplicative → Unary { STAR Unary }
...
```

Дерево разбора:
```
Additive
├── Multiplicative (a)
└── PLUS
    └── Multiplicative
        ├── Unary (b)
        └── STAR
            └── Unary (c)
```
