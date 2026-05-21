from typing import List, Optional, Any
from src.lexer.token import Token, TokenType
from src.parser.ast import *


class ParseError(Exception):
    """Исключение для синтаксических ошибок."""
    def __init__(self, message: str, token: Token):
        self.message = message
        self.token = token
        super().__init__(f"{message} at {token.line}:{token.column}")


class Parser:
    """Рекурсивный нисходящий парсер для MiniCompiler (LL(1))."""

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.current = 0
        self.errors: List[ParseError] = []

    # ============ Базовые методы ============

    def is_at_end(self) -> bool:
        """Проверяет, достигнут ли конец потока токенов."""
        return self.peek().type == TokenType.END_OF_FILE

    def peek(self) -> Token:
        """Возвращает текущий токен без продвижения."""
        if self.current >= len(self.tokens):
            return Token(TokenType.END_OF_FILE, "", 0, 0)
        return self.tokens[self.current]

    def peek_next(self) -> Token:
        """Возвращает следующий токен (через один) без продвижения."""
        if self.current + 1 >= len(self.tokens):
            return Token(TokenType.END_OF_FILE, "", 0, 0)
        return self.tokens[self.current + 1]

    def previous(self) -> Token:
        """Возвращает предыдущий токен (после вызова advance)."""
        return self.tokens[self.current - 1]

    def advance(self) -> Token:
        """Продвигается на один токен вперёд и возвращает предыдущий."""
        if not self.is_at_end():
            self.current += 1
        return self.previous()

    def check(self, token_type: TokenType) -> bool:
        """Проверяет, является ли текущий токен заданным типом."""
        if self.is_at_end():
            return False
        return self.peek().type == token_type

    def match(self, *types: TokenType) -> bool:
        """Если текущий токен совпадает с одним из переданных типов, продвигается и возвращает True."""
        for t in types:
            if self.check(t):
                self.advance()
                return True
        return False

    def consume(self, token_type: TokenType, message: str) -> Token:
        """Потребляет токен ожидаемого типа или выбрасывает ошибку."""
        if self.check(token_type):
            return self.advance()
        if token_type == TokenType.SEMICOLON:
            message += " (возможно, пропущена ';')"
        elif token_type == TokenType.RPAREN:
            message += " (возможно, пропущена ')')"
        elif token_type == TokenType.RBRACE:
            message += " (возможно, пропущена '}')"
        elif token_type == TokenType.LBRACE:
            message += " (возможно, пропущена '{')"
        error = ParseError(message, self.peek())
        self.errors.append(error)
        raise error

    def synchronize(self):
        """Синхронизируется после ошибки: пропускает токены до границы оператора/объявления."""
        self.advance()
        while not self.is_at_end():
            if self.previous().type == TokenType.SEMICOLON:
                return
            t = self.peek().type
            if t in (TokenType.KW_FN, TokenType.KW_STRUCT, TokenType.KW_INT,
                     TokenType.KW_FLOAT, TokenType.KW_BOOL, TokenType.KW_VOID,
                     TokenType.KW_IF, TokenType.KW_WHILE, TokenType.KW_FOR,
                     TokenType.KW_RETURN, TokenType.LBRACE, TokenType.RBRACE):
                return
            self.advance()

    # ============ Методы разбора ============

    def parse(self) -> ProgramNode:
        """Разбирает всю программу."""
        try:
            declarations = []
            while not self.is_at_end():
                decl = self.declaration()
                if decl:
                    declarations.append(decl)
            # Позиция программы — позиция первого токена или 1:1
            line = 1
            column = 1
            if self.tokens:
                line = self.tokens[0].line
                column = self.tokens[0].column
            return ProgramNode(declarations, line, column)
        except ParseError as e:
            self.errors.append(e)
            self.synchronize()
            return ProgramNode([], 1, 1)

    def declaration(self) -> Optional[ASTNode]:
        try:
            # Объявление переменной с выводом типа (var)
            if self.match(TokenType.KW_VAR):
                return self.var_declaration()

            if self.match(TokenType.KW_FN):
                return self.function_declaration()

            if self.match(TokenType.KW_STRUCT):
                if not self.check(TokenType.IDENTIFIER):
                    raise ParseError("Ожидается имя структуры", self.peek())
                # безопасный предпросмотр
                if self.peek_next().type == TokenType.LBRACE:
                    return self.struct_declaration()
                else:
                    ident_token = self.advance()
                    type_name = f"struct {ident_token.lexeme}"
                    return self.variable_declaration_with_type(type_name)

            if self.match(TokenType.KW_INT, TokenType.KW_FLOAT, TokenType.KW_BOOL, TokenType.KW_VOID):
                type_name = self.previous().lexeme
                return self.variable_declaration_with_type(type_name)

            return self.statement()
        except ParseError:
            self.synchronize()
            return None

    def variable_declaration_with_type(self, type_name: str) -> VarDeclNode:
        name_token = self.consume(TokenType.IDENTIFIER, "Ожидается имя переменной")
        name = name_token.lexeme
        initializer = None
        if self.match(TokenType.ASSIGN):
            initializer = self.expression()
        self.consume(TokenType.SEMICOLON, "Ожидается ';' после объявления переменной")
        return VarDeclNode(type_name, name, initializer, name_token.line, name_token.column)

    def function_declaration(self) -> FunctionDeclNode:
        line = self.previous().line
        column = self.previous().column
        name_token = self.consume(TokenType.IDENTIFIER, "Ожидается имя функции")
        name = name_token.lexeme
        self.consume(TokenType.LPAREN, "Ожидается '(' после имени функции")
        parameters = self.parameters()
        self.consume(TokenType.RPAREN, "Ожидается ')' после параметров")
        return_type = "void"
        if self.match(TokenType.ARROW):
            return_type = self.type_name()
        elif self.match(TokenType.COLON):
            return_type = self.type_name()
        body = self.block()
        return FunctionDeclNode(return_type, name, parameters, body, line, column)

    def struct_declaration(self) -> StructDeclNode:
        line = self.previous().line
        column = self.previous().column
        name_token = self.consume(TokenType.IDENTIFIER, "Ожидается имя структуры")
        name = name_token.lexeme
        self.consume(TokenType.LBRACE, "Ожидается '{' после имени структуры")
        fields = []
        while not self.check(TokenType.RBRACE) and not self.is_at_end():
            field = self.variable_declaration()
            if field:
                fields.append(field)
        self.consume(TokenType.RBRACE, "Ожидается '}' после полей структуры")
        return StructDeclNode(name, fields, line, column)

    def variable_declaration(self) -> VarDeclNode:
        type_name = self.type_name()
        name_token = self.consume(TokenType.IDENTIFIER, "Ожидается имя переменной")
        name = name_token.lexeme
        initializer = None
        if self.match(TokenType.ASSIGN):
            initializer = self.expression()
        self.consume(TokenType.SEMICOLON, "Ожидается ';' после объявления переменной")
        return VarDeclNode(type_name, name, initializer, name_token.line, name_token.column)

    def type_name(self) -> str:
        if self.check(TokenType.KW_VAR):
            raise ParseError("'var' не является типом; используйте 'var' для объявления переменной с выводом типа", self.peek())
        if self.match(TokenType.KW_INT):
            return "int"
        if self.match(TokenType.KW_FLOAT):
            return "float"
        if self.match(TokenType.KW_BOOL):
            return "bool"
        if self.match(TokenType.KW_VOID):
            return "void"
        if self.match(TokenType.KW_STRUCT):
            name_token = self.consume(TokenType.IDENTIFIER, "Ожидается имя структуры")
            return f"struct {name_token.lexeme}"
        raise ParseError("Ожидается тип", self.peek())

    def parameters(self) -> List[ParamNode]:
        params = []
        if not self.check(TokenType.RPAREN):
            param_type = self.type_name()
            name_token = self.consume(TokenType.IDENTIFIER, "Ожидается имя параметра")
            params.append(ParamNode(param_type, name_token.lexeme, name_token.line, name_token.column))
            while self.match(TokenType.COMMA):
                param_type = self.type_name()
                name_token = self.consume(TokenType.IDENTIFIER, "Ожидается имя параметра")
                params.append(ParamNode(param_type, name_token.lexeme, name_token.line, name_token.column))
        return params

    def block(self) -> BlockStmtNode:
        line = self.peek().line
        column = self.peek().column
        self.consume(TokenType.LBRACE, "Ожидается '{' для блока")
        statements = []
        while not self.check(TokenType.RBRACE) and not self.is_at_end():
            stmt = self.declaration()
            if stmt:
                statements.append(stmt)
        self.consume(TokenType.RBRACE, "Ожидается '}' после блока")
        return BlockStmtNode(statements, line, column)

    def statement(self) -> Optional[ASTNode]:
        if self.check(TokenType.LBRACE):
            return self.block()
        if self.match(TokenType.KW_IF):
            return self.if_statement()
        if self.match(TokenType.KW_WHILE):
            return self.while_statement()
        if self.match(TokenType.KW_FOR):
            return self.for_statement()
        if self.match(TokenType.KW_RETURN):
            return self.return_statement()
        if self.match(TokenType.SEMICOLON):
            return EmptyStmtNode(self.previous().line, self.previous().column)
        return self.expression_statement()

    def if_statement(self) -> IfStmtNode:
        line = self.previous().line
        column = self.previous().column
        self.consume(TokenType.LPAREN, "Ожидается '(' после 'if'")
        condition = self.expression()
        self.consume(TokenType.RPAREN, "Ожидается ')' после условия")
        then_branch = self.statement()
        else_branch = None
        if self.match(TokenType.KW_ELSE):
            else_branch = self.statement()
        return IfStmtNode(condition, then_branch, else_branch, line, column)

    def while_statement(self) -> WhileStmtNode:
        line = self.previous().line
        column = self.previous().column
        self.consume(TokenType.LPAREN, "Ожидается '(' после 'while'")
        condition = self.expression()
        self.consume(TokenType.RPAREN, "Ожидается ')' после условия")
        body = self.statement()
        return WhileStmtNode(condition, body, line, column)

    def for_statement(self) -> ForStmtNode:
        line = self.previous().line
        column = self.previous().column
        self.consume(TokenType.LPAREN, "Ожидается '(' после 'for'")

        init = None
        has_semicolon_after_init = False  # флаг, что ';' уже съедена
        if not self.check(TokenType.SEMICOLON):
            saved = self.current
            try:
                # Пробуем разобрать VarDecl (начинается с типа)
                if self.check(TokenType.KW_INT) or self.check(TokenType.KW_FLOAT) or \
                        self.check(TokenType.KW_BOOL) or self.check(TokenType.KW_VOID) or \
                        self.check(TokenType.KW_STRUCT):
                    init = self.variable_declaration()
                    has_semicolon_after_init = True  # variable_declaration съел ';'
                else:
                    expr = self.expression()
                    init = ExprStmtNode(expr, expr.line, expr.column)
            except ParseError:
                self.current = saved
                expr = self.expression()
                init = ExprStmtNode(expr, expr.line, expr.column)

        # Если ';' ещё не съедена, потребляем её
        if not has_semicolon_after_init:
            self.consume(TokenType.SEMICOLON, "Ожидается ';' после инициализации for")

        # Условие
        condition = None
        if not self.check(TokenType.SEMICOLON):
            condition = self.expression()
        self.consume(TokenType.SEMICOLON, "Ожидается ';' после условия for")

        # Обновление
        update = None
        if not self.check(TokenType.RPAREN):
            update = self.expression()
        self.consume(TokenType.RPAREN, "Ожидается ')' после заголовка for")

        body = self.statement()
        return ForStmtNode(init, condition, update, body, line, column)

    def return_statement(self) -> ReturnStmtNode:
        line = self.previous().line
        column = self.previous().column
        value = None
        if not self.check(TokenType.SEMICOLON):
            value = self.expression()
        self.consume(TokenType.SEMICOLON, "Ожидается ';' после return")
        return ReturnStmtNode(value, line, column)

    def expression_statement(self) -> ExprStmtNode:
        expr = self.expression()
        self.consume(TokenType.SEMICOLON, "Ожидается ';' после выражения")
        return ExprStmtNode(expr, expr.line, expr.column)

    # ============ Разбор выражений (с приоритетами) ============

    def expression(self) -> ExpressionNode:
        return self.assignment()

    def assignment(self) -> ExpressionNode:
        left = self.logical_or()
        if self.match(TokenType.ASSIGN, TokenType.ADD_ASSIGN, TokenType.SUB_ASSIGN,
                      TokenType.MUL_ASSIGN, TokenType.DIV_ASSIGN):
            op = self.previous().type
            if not isinstance(left, IdentifierExprNode):
                error = ParseError("Левая часть присваивания должна быть идентификатором", self.previous())
                self.errors.append(error)
                raise error
            right = self.assignment()
            return AssignmentExprNode(left.name, op, right, left.line, left.column)
        return left

    def logical_or(self) -> ExpressionNode:
        expr = self.logical_and()
        while self.match(TokenType.OR):
            op = self.previous().type
            right = self.logical_and()
            expr = BinaryExprNode(expr, op, right, expr.line, expr.column)
        return expr

    def logical_and(self) -> ExpressionNode:
        expr = self.equality()
        while self.match(TokenType.AND):
            op = self.previous().type
            right = self.equality()
            expr = BinaryExprNode(expr, op, right, expr.line, expr.column)
        return expr

    def equality(self) -> ExpressionNode:
        expr = self.relational()
        while self.match(TokenType.EQ, TokenType.NE):
            op = self.previous().type
            right = self.relational()
            expr = BinaryExprNode(expr, op, right, expr.line, expr.column)
        return expr

    def relational(self) -> ExpressionNode:
        expr = self.additive()
        while self.match(TokenType.LT, TokenType.LE, TokenType.GT, TokenType.GE):
            op = self.previous().type
            right = self.additive()
            expr = BinaryExprNode(expr, op, right, expr.line, expr.column)
        return expr

    def additive(self) -> ExpressionNode:
        expr = self.multiplicative()
        while self.match(TokenType.PLUS, TokenType.MINUS):
            op = self.previous().type
            right = self.multiplicative()
            expr = BinaryExprNode(expr, op, right, expr.line, expr.column)
        return expr

    def multiplicative(self) -> ExpressionNode:
        expr = self.unary()
        while self.match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self.previous().type
            right = self.unary()
            expr = BinaryExprNode(expr, op, right, expr.line, expr.column)
        return expr

    def unary(self) -> ExpressionNode:
        if self.match(TokenType.MINUS, TokenType.NOT, TokenType.INC_OP, TokenType.DEC_OP):
            op = self.previous().type
            operand = self.unary()
            return UnaryExprNode(op, operand, self.previous().line, self.previous().column)
        return self.postfix()

    def postfix(self) -> ExpressionNode:
        expr = self.call()
        while self.match(TokenType.INC_OP, TokenType.DEC_OP):
            op = self.previous().type
            expr = PostfixExprNode(op, expr, self.previous().line, self.previous().column)
        return expr

    def call(self) -> ExpressionNode:
        expr = self.primary()
        while self.match(TokenType.LPAREN):
            args = []
            if not self.check(TokenType.RPAREN):
                args.append(self.expression())
                while self.match(TokenType.COMMA):
                    args.append(self.expression())
            self.consume(TokenType.RPAREN, "Ожидается ')' после аргументов")
            if not isinstance(expr, IdentifierExprNode):
                error = ParseError("Можно вызывать только функции (идентификаторы)", self.previous())
                self.errors.append(error)
                raise error
            expr = CallExprNode(expr.name, args, expr.line, expr.column)
        return expr

    def primary(self) -> ExpressionNode:
        if self.match(TokenType.INT_LITERAL):
            token = self.previous()
            return LiteralExprNode(token.literal, TokenType.INT_LITERAL, token.line, token.column)
        if self.match(TokenType.FLOAT_LITERAL):
            token = self.previous()
            return LiteralExprNode(token.literal, TokenType.FLOAT_LITERAL, token.line, token.column)
        if self.match(TokenType.STRING_LITERAL):
            token = self.previous()
            return LiteralExprNode(token.literal, TokenType.STRING_LITERAL, token.line, token.column)
        if self.match(TokenType.KW_TRUE):
            token = self.previous()
            return LiteralExprNode(True, TokenType.KW_TRUE, token.line, token.column)
        if self.match(TokenType.KW_FALSE):
            token = self.previous()
            return LiteralExprNode(False, TokenType.KW_FALSE, token.line, token.column)
        if self.match(TokenType.IDENTIFIER):
            token = self.previous()
            return IdentifierExprNode(token.lexeme, token.line, token.column)
        if self.match(TokenType.LPAREN):
            expr = self.expression()
            self.consume(TokenType.RPAREN, "Ожидается ')' после выражения")
            return expr
        error = ParseError("Ожидается выражение", self.peek())
        self.errors.append(error)
        raise error

    def var_declaration(self) -> VarDeclNode:
        line = self.previous().line
        column = self.previous().column
        name_token = self.consume(TokenType.IDENTIFIER, "Ожидается имя переменной после 'var'")
        name = name_token.lexeme
        initializer = None
        if self.match(TokenType.ASSIGN):
            initializer = self.expression()
        self.consume(TokenType.SEMICOLON, "Ожидается ';' после объявления переменной")
        return VarDeclNode("var", name, initializer, line, column)