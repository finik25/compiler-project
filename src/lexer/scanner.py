from typing import Optional
from src.lexer.token import Token, TokenType

class Scanner:
    def __init__(self, source: str):
        self.source = source
        self.start = 0          # начало текущего лексемы
        self.current = 0        # текущая позиция в строке
        self.line = 1
        self.column = 1
        self._peek_token = None   # буфер для lookahead (peek_token)

        # Карта ключевых слов
        self.keywords = {
            "if": TokenType.KW_IF,
            "else": TokenType.KW_ELSE,
            "while": TokenType.KW_WHILE,
            "for": TokenType.KW_FOR,
            "int": TokenType.KW_INT,
            "float": TokenType.KW_FLOAT,
            "bool": TokenType.KW_BOOL,
            "return": TokenType.KW_RETURN,
            "true": TokenType.KW_TRUE,
            "false": TokenType.KW_FALSE,
            "void": TokenType.KW_VOID,
            "struct": TokenType.KW_STRUCT,
            "fn": TokenType.KW_FN,
        }

        # Карта двухсимвольных операторов (для справки, не используется напрямую)
        self.two_char_ops = {
            "==": TokenType.EQ,
            "!=": TokenType.NE,
            "<=": TokenType.LE,
            ">=": TokenType.GE,
            "&&": TokenType.AND,
            "||": TokenType.OR,
            "++": TokenType.INC_OP,
            "--": TokenType.DEC_OP,
            "+=": TokenType.ADD_ASSIGN,
            "-=": TokenType.SUB_ASSIGN,
            "*=": TokenType.MUL_ASSIGN,
            "/=": TokenType.DIV_ASSIGN,
        }

    def is_at_end(self) -> bool:
        """Проверяет, достигнут ли конец исходного кода."""
        return self.current >= len(self.source)

    def advance(self) -> str:
        """Возвращает текущий символ и сдвигает указатель вперёд,
        обновляя позицию (строку и столбец)."""
        ch = self.source[self.current]
        self.current += 1
        if ch == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def peek(self) -> str:
        """Возвращает текущий символ без сдвига. Если конец, возвращает '\0'."""
        if self.is_at_end():
            return '\0'
        return self.source[self.current]

    def peek_next(self) -> str:
        """Возвращает следующий символ (без сдвига) или '\0', если его нет."""
        if self.current + 1 >= len(self.source):
            return '\0'
        return self.source[self.current + 1]

    def match(self, expected: str) -> bool:
        """Если следующий символ равен expected, сдвигаем (advance) и возвращаем True."""
        if self.is_at_end() or self.source[self.current] != expected:
            return False
        self.advance()
        return True

    def skip_whitespace(self):
        """Пропускает пробельные символы (пробел, табуляция, возврат каретки, перевод строки)."""
        while not self.is_at_end():
            ch = self.peek()
            if ch in (' ', '\t', '\r', '\n'):
                self.advance()
            else:
                break

    def _make_token(self, token_type: TokenType, literal=None) -> Token:
        """Создаёт токен от self.start до self.current, сбрасывая start."""
        lexeme = self.source[self.start:self.current]
        token = Token(token_type, lexeme, self.line, self.column - len(lexeme), literal)
        self.start = self.current
        return token

    def _error_token(self, message: str) -> Token:
        """Создаёт токен ошибки, используя текущий символ (или следующий) как лексему."""
        # Если мы уже съели символ, то self.start указывает на начало ошибки,
        # иначе (если вызвано без продвижения) нужно продвинуться, чтобы захватить символ.
        if self.start == self.current and not self.is_at_end():
            self.advance()
        lexeme = self.source[self.start:self.current]
        token = Token(TokenType.ERROR, lexeme, self.line, self.column - len(lexeme), message)
        self.start = self.current
        return token

    def scan_token(self) -> Token:
        """Распознаёт следующий токен и возвращает его."""
        self.skip_whitespace()
        self.start = self.current

        if self.is_at_end():
            return self._make_token(TokenType.END_OF_FILE)

        ch = self.advance()

        # Простые односимвольные токены
        if ch == '(':
            return self._make_token(TokenType.LPAREN)
        if ch == ')':
            return self._make_token(TokenType.RPAREN)
        if ch == '{':
            return self._make_token(TokenType.LBRACE)
        if ch == '}':
            return self._make_token(TokenType.RBRACE)
        if ch == '[':
            return self._make_token(TokenType.LBRACKET)
        if ch == ']':
            return self._make_token(TokenType.RBRACKET)
        if ch == ';':
            return self._make_token(TokenType.SEMICOLON)
        if ch == ',':
            return self._make_token(TokenType.COMMA)
        if ch == ':':
            return self._make_token(TokenType.COLON)

        # Операторы (одно- и двухсимвольные)
        if ch == '+':
            if self.peek() == '+':
                self.advance()
                return self._make_token(TokenType.INC_OP)
            elif self.peek() == '=':
                self.advance()
                return self._make_token(TokenType.ADD_ASSIGN)
            return self._make_token(TokenType.PLUS)

        if ch == '-':
            if self.peek() == '-':
                self.advance()
                return self._make_token(TokenType.DEC_OP)
            elif self.peek() == '=':
                self.advance()
                return self._make_token(TokenType.SUB_ASSIGN)
            return self._make_token(TokenType.MINUS)

        if ch == '*':
            if self.peek() == '=':
                self.advance()
                return self._make_token(TokenType.MUL_ASSIGN)
            return self._make_token(TokenType.STAR)

        if ch == '/':
            if self.peek() == '/':
                # однострочный комментарий
                while not self.is_at_end() and self.peek() != '\n':
                    self.advance()
                return self.scan_token()
            elif self.peek() == '*':
                # многострочный комментарий: запоминаем начало
                start_line = self.line
                start_column = self.column - 1  # позиция символа '/'
                self.advance()  # съедаем '*'
                while not self.is_at_end():
                    if self.peek() == '*' and self.peek_next() == '/':
                        self.advance()  # съедаем '*'
                        self.advance()  # съедаем '/'
                        break
                    self.advance()
                else:
                    # комментарий не закрыт
                    lexeme = self.source[self.start:self.current]
                    # сбрасываем start, чтобы следующий токен начался с текущей позиции
                    self.start = self.current
                    return Token(TokenType.ERROR, lexeme, start_line, start_column, "Unterminated comment")
                return self.scan_token()
            elif self.peek() == '=':
                self.advance()
                return self._make_token(TokenType.DIV_ASSIGN)
            else:
                return self._make_token(TokenType.SLASH)

        if ch == '%':
            return self._make_token(TokenType.PERCENT)

        if ch == '=':
            if self.peek() == '=':
                self.advance()
                return self._make_token(TokenType.EQ)
            return self._make_token(TokenType.ASSIGN)

        if ch == '!':
            if self.peek() == '=':
                self.advance()
                return self._make_token(TokenType.NE)
            return self._make_token(TokenType.NOT)

        if ch == '<':
            if self.peek() == '=':
                self.advance()
                return self._make_token(TokenType.LE)
            return self._make_token(TokenType.LT)

        if ch == '>':
            if self.peek() == '=':
                self.advance()
                return self._make_token(TokenType.GE)
            return self._make_token(TokenType.GT)

        if ch == '&':
            if self.peek() == '&':
                self.advance()
                return self._make_token(TokenType.AND)
            return self._error_token(f"Unexpected character '{ch}' (did you mean '&&'?)")

        if ch == '|':
            if self.peek() == '|':
                self.advance()
                return self._make_token(TokenType.OR)
            return self._error_token(f"Unexpected character '{ch}' (did you mean '||'?)")

        # Идентификаторы и ключевые слова
        if ch.isalpha() or ch == '_':
            while self.peek().isalnum() or self.peek() == '_':
                self.advance()
            lexeme = self.source[self.start:self.current]
            token_type = self.keywords.get(lexeme, TokenType.IDENTIFIER)
            return self._make_token(token_type)

        # Числа
        if ch.isdigit():
            while self.peek().isdigit():
                self.advance()
            # Если дальше точка и ещё цифры, то float
            if self.peek() == '.' and self.peek_next().isdigit():
                self.advance()  # точка
                while self.peek().isdigit():
                    self.advance()
                value = float(self.source[self.start:self.current])
                return self._make_token(TokenType.FLOAT_LITERAL, value)
            else:
                value = int(self.source[self.start:self.current])
                return self._make_token(TokenType.INT_LITERAL, value)

        # Строковые литералы
        if ch == '"':
            start_line = self.line
            start_column = self.column - 1  # позиция открывающей кавычки
            string_chars = []
            while not self.is_at_end() and self.peek() != '"':
                string_chars.append(self.advance())
            if self.is_at_end():
                lexeme = self.source[self.start:self.current]
                self.start = self.current
                return Token(TokenType.ERROR, lexeme, start_line, start_column, "Unterminated string")
            self.advance()  # закрывающая кавычка
            literal = ''.join(string_chars)
            return self._make_token(TokenType.STRING_LITERAL, literal)

        # Если ничего не подошло — недопустимый символ
        return self._error_token(f"Unexpected character '{ch}'")

    def next_token(self) -> Token:
        """Возвращает следующий токен и продвигает поток."""
        if self._peek_token is not None:
            token = self._peek_token
            self._peek_token = None
            return token
        return self.scan_token()

    def peek_token(self) -> Token:
        """Возвращает следующий токен без продвижения."""
        if self._peek_token is None:
            self._peek_token = self.scan_token()
        return self._peek_token