from typing import List, Optional
from src.parser.ast import *
from src.semantic.symbol_table import SymbolTable, Symbol, SymbolKind
from src.semantic.type_system import is_compatible, get_binary_result_type, get_unary_result_type
from src.semantic.errors import SemanticError
from src.lexer.token import TokenType


class SemanticAnalyzer:
    def __init__(self):
        self.symbol_table = SymbolTable()
        self.errors: List[SemanticError] = []
        self.current_function: Optional[Symbol] = None
        self.in_loop = False

    def analyze(self, program: ProgramNode):
        # Первый проход: регистрация глобальных объявлений
        for decl in program.declarations:
            if isinstance(decl, FunctionDeclNode):
                self._register_function(decl)
            elif isinstance(decl, StructDeclNode):
                self._register_struct(decl)
            elif isinstance(decl, VarDeclNode):
                self._register_global_variable(decl)

        # Второй проход: анализ тел функций и инициализаторов глобальных переменных
        for decl in program.declarations:
            if isinstance(decl, FunctionDeclNode):
                self._analyze_function(decl)
        for decl in program.declarations:
            if isinstance(decl, VarDeclNode) and decl.initializer:
                self._analyze_global_initializer(decl)

        return self.symbol_table, self.errors

    def get_report(self) -> str:
        lines = []
        lines.append(f"Semantic analysis completed with {len(self.errors)} error(s).")
        lines.append("\nSymbol Table:")
        lines.append(self.symbol_table.dump())
        lines.append("\nType Hierarchy:")
        lines.append("  - Primitive types: int, float, bool, void, string")
        structs = []
        for scope in self.symbol_table.scopes:
            for sym in scope.values():
                if sym.kind == SymbolKind.STRUCT:
                    structs.append(sym.name)
        if structs:
            lines.append(f"  - Detected structs: {', '.join(structs)}")
        else:
            lines.append("  - Struct types: (none detected)")
        return "\n".join(lines)

    # ---------- Первый проход: регистрация ----------
    def _register_function(self, node: FunctionDeclNode):
        existing = self.symbol_table.lookup(node.name)
        if existing:
            self.errors.append(SemanticError(f"Duplicate function '{node.name}'", node.line, node.column))
            return
        func_sym = Symbol(node.name, SymbolKind.FUNCTION, node.return_type, node.line, node.column,
                          params=[], return_type=node.return_type)
        self.symbol_table.insert(node.name, func_sym)

    def _register_struct(self, node: StructDeclNode):
        existing = self.symbol_table.lookup(node.name)
        if existing:
            self.errors.append(SemanticError(f"Duplicate struct '{node.name}'", node.line, node.column))
            return
        struct_sym = Symbol(node.name, SymbolKind.STRUCT, node.name, node.line, node.column)
        self.symbol_table.enter_scope()
        for field in node.fields:
            field_sym = Symbol(field.name, SymbolKind.VARIABLE, field.type_name, field.line, field.column)
            if not self.symbol_table.insert(field.name, field_sym):
                self.errors.append(SemanticError(f"Duplicate field '{field.name}' in struct '{node.name}'", field.line, field.column))
            struct_sym.fields[field.name] = field_sym
        self.symbol_table.exit_scope()
        self.symbol_table.insert(node.name, struct_sym)

    def _register_global_variable(self, node: VarDeclNode):
        existing = self.symbol_table.lookup(node.name)
        if existing:
            self.errors.append(SemanticError(f"Duplicate global variable '{node.name}'", node.line, node.column))
            return
        var_sym = Symbol(node.name, SymbolKind.VARIABLE, node.type_name, node.line, node.column)
        self.symbol_table.insert(node.name, var_sym)

    # ---------- Второй проход: анализ тел ----------
    def _analyze_function(self, node: FunctionDeclNode):
        func_sym = self.symbol_table.lookup(node.name)
        if not func_sym:
            return
        self.current_function = func_sym
        self.symbol_table.enter_scope()
        # Добавляем параметры
        for param in node.parameters:
            param_sym = Symbol(param.name, SymbolKind.PARAMETER, param.type_name, param.line, param.column)
            if not self.symbol_table.insert(param.name, param_sym):
                self.errors.append(SemanticError(f"Duplicate parameter name '{param.name}' in function '{node.name}'", param.line, param.column))
            func_sym.params.append(param_sym)
        # Анализируем тело
        if node.body:
            self._analyze_block(node.body, func_sym.return_type)
        else:
            self.errors.append(SemanticError(f"Function '{node.name}' has no body", node.line, node.column))
        self.symbol_table.exit_scope()
        self.current_function = None

    def _analyze_block(self, block: BlockStmtNode, expected_return_type: Optional[str] = None):
        self.symbol_table.enter_scope()
        for stmt in block.statements:
            self._analyze_statement(stmt, expected_return_type)
        self.symbol_table.exit_scope()

    def _analyze_statement(self, stmt: ASTNode, expected_return_type: Optional[str] = None):
        if isinstance(stmt, VarDeclNode):
            self._analyze_var_decl(stmt)
        elif isinstance(stmt, ExprStmtNode):
            self._analyze_expression(stmt.expression)
        elif isinstance(stmt, IfStmtNode):
            self._analyze_if(stmt, expected_return_type)
        elif isinstance(stmt, WhileStmtNode):
            self._analyze_while(stmt, expected_return_type)
        elif isinstance(stmt, ForStmtNode):
            self._analyze_for(stmt, expected_return_type)
        elif isinstance(stmt, ReturnStmtNode):
            self._analyze_return(stmt, expected_return_type)
        elif isinstance(stmt, BlockStmtNode):
            self._analyze_block(stmt, expected_return_type)
        elif isinstance(stmt, EmptyStmtNode):
            pass
        else:
            self.errors.append(SemanticError(f"Unknown statement type: {type(stmt).__name__}", stmt.line, stmt.column))

    # ---------- Анализ объявления переменной (с поддержкой var и error propagation) ----------
    def _analyze_var_decl(self, node: VarDeclNode):
        if self.symbol_table.lookup_local(node.name):
            self.errors.append(SemanticError(f"Duplicate variable '{node.name}' in same scope", node.line, node.column))
            return

        # Анализ инициализатора
        init_type = None
        if node.initializer:
            init_type = self._analyze_expression(node.initializer)

        final_type = node.type_name

        # Если тип "var" – выводим из инициализатора
        if node.type_name == "var":
            if not node.initializer:
                self.errors.append(SemanticError("'var' declaration requires an initializer", node.line, node.column))
                return
            if init_type == "error":
                final_type = "error"
            else:
                final_type = init_type
                node.type_name = final_type   # декорируем узел
        else:
            # Обычный тип: проверяем совместимость с инициализатором, если он есть
            if init_type and init_type != "error":
                if not is_compatible(node.type_name, init_type):
                    self.errors.append(SemanticError(
                        f"Type mismatch in initialization: expected '{node.type_name}', got '{init_type}'",
                        node.line, node.column
                    ))
                    final_type = "error"
            elif init_type == "error":
                final_type = "error"

        # Создаём символ (даже с типом "error" – чтобы избежать undeclared cascade)
        var_sym = Symbol(node.name, SymbolKind.VARIABLE, final_type, node.line, node.column)
        self.symbol_table.insert(node.name, var_sym)

    # ---------- Анализ выражений (с распространением ошибок) ----------
    def _analyze_expression(self, expr: ExpressionNode) -> str:
        """Возвращает тип выражения или 'error'."""
        if isinstance(expr, LiteralExprNode):
            if expr.literal_type in (TokenType.INT_LITERAL, TokenType.KW_TRUE, TokenType.KW_FALSE):
                t = "int" if expr.literal_type == TokenType.INT_LITERAL else "bool"
            elif expr.literal_type == TokenType.FLOAT_LITERAL:
                t = "float"
            elif expr.literal_type == TokenType.STRING_LITERAL:
                t = "string"
            else:
                t = "unknown"
            expr.type_annotation = t
            return t

        elif isinstance(expr, IdentifierExprNode):
            sym = self.symbol_table.lookup(expr.name)
            if not sym:
                self.errors.append(SemanticError(f"Undeclared identifier '{expr.name}'", expr.line, expr.column))
                expr.type_annotation = "error"
                return "error"
            expr.symbol = sym
            expr.type_annotation = sym.type_name
            # Если символ имеет тип "error", не генерируем новую ошибку
            return sym.type_name

        elif isinstance(expr, BinaryExprNode):
            left_type = self._analyze_expression(expr.left)
            right_type = self._analyze_expression(expr.right)
            if left_type == "error" or right_type == "error":
                expr.type_annotation = "error"
                return "error"
            result_type = get_binary_result_type(expr.operator, left_type, right_type)
            if result_type is None:
                self.errors.append(SemanticError(
                    f"Type mismatch in binary operation '{expr.operator.name}': '{left_type}' and '{right_type}'",
                    expr.line, expr.column
                ))
                expr.type_annotation = "error"
                return "error"
            expr.type_annotation = result_type
            return result_type

        elif isinstance(expr, UnaryExprNode):
            operand_type = self._analyze_expression(expr.operand)
            if operand_type == "error":
                expr.type_annotation = "error"
                return "error"
            result_type = get_unary_result_type(expr.operator, operand_type)
            if result_type is None:
                self.errors.append(SemanticError(
                    f"Unary operator '{expr.operator.name}' cannot be applied to type '{operand_type}'",
                    expr.line, expr.column
                ))
                expr.type_annotation = "error"
                return "error"
            expr.type_annotation = result_type
            return result_type

        elif isinstance(expr, PostfixExprNode):
            operand_type = self._analyze_expression(expr.operand)
            if operand_type == "error":
                expr.type_annotation = "error"
                return "error"
            if operand_type not in ("int", "float"):
                self.errors.append(SemanticError(
                    f"Postfix operator '{expr.operator.name}' requires numeric type, got '{operand_type}'",
                    expr.line, expr.column
                ))
                expr.type_annotation = "error"
                return "error"
            expr.type_annotation = operand_type
            return operand_type

        elif isinstance(expr, CallExprNode):
            sym = self.symbol_table.lookup(expr.callee)
            if not sym or sym.kind != SymbolKind.FUNCTION:
                self.errors.append(SemanticError(f"Call to undeclared function '{expr.callee}'", expr.line, expr.column))
                expr.type_annotation = "error"
                return "error"
            expr.function_symbol = sym
            # Проверка аргументов (с учётом error propagation)
            if len(expr.arguments) != len(sym.params):
                self.errors.append(SemanticError(
                    f"Argument count mismatch for function '{expr.callee}': expected {len(sym.params)}, got {len(expr.arguments)}",
                    expr.line, expr.column
                ))
            arg_has_error = False
            for i, arg in enumerate(expr.arguments):
                arg_type = self._analyze_expression(arg)
                if arg_type == "error":
                    arg_has_error = True
                    continue
                if i < len(sym.params):
                    expected = sym.params[i].type_name
                    if not is_compatible(expected, arg_type):
                        self.errors.append(SemanticError(
                            f"Argument {i+1} type mismatch: expected '{expected}', got '{arg_type}'",
                            arg.line, arg.column
                        ))
            if arg_has_error:
                expr.type_annotation = "error"
                return "error"
            expr.type_annotation = sym.return_type
            return sym.return_type

        elif isinstance(expr, AssignmentExprNode):
            target_sym = self.symbol_table.lookup(expr.target)
            if not target_sym:
                self.errors.append(SemanticError(f"Assignment to undeclared variable '{expr.target}'", expr.line, expr.column))
                expr.type_annotation = "error"
                return "error"
            right_type = self._analyze_expression(expr.value)
            if right_type == "error" or target_sym.type_name == "error":
                expr.type_annotation = "error"
                return "error"
            if not is_compatible(target_sym.type_name, right_type):
                self.errors.append(SemanticError(
                    f"Assignment type mismatch: variable '{expr.target}' is '{target_sym.type_name}', expression is '{right_type}'",
                    expr.value.line, expr.value.column
                ))
                expr.type_annotation = "error"
                return "error"
            # Составные присваивания требуют числового типа
            if expr.operator != TokenType.ASSIGN:
                if target_sym.type_name not in ("int", "float"):
                    self.errors.append(SemanticError(
                        f"Compound assignment operator requires numeric type, but '{expr.target}' is '{target_sym.type_name}'",
                        expr.line, expr.column
                    ))
                    expr.type_annotation = "error"
                    return "error"
            expr.type_annotation = target_sym.type_name
            return target_sym.type_name

        else:
            self.errors.append(SemanticError(f"Unknown expression type: {type(expr).__name__}", expr.line, expr.column))
            return "error"

    # ---------- Анализ управляющих конструкций ----------
    def _analyze_if(self, node: IfStmtNode, expected_return_type: Optional[str] = None):
        cond_type = self._analyze_expression(node.condition)
        if cond_type != "bool" and cond_type != "error":
            self.errors.append(SemanticError(f"Condition in 'if' must be boolean, got '{cond_type}'", node.condition.line, node.condition.column))
        self._analyze_statement(node.then_branch, expected_return_type)
        if node.else_branch:
            self._analyze_statement(node.else_branch, expected_return_type)

    def _analyze_while(self, node: WhileStmtNode, expected_return_type: Optional[str] = None):
        cond_type = self._analyze_expression(node.condition)
        if cond_type != "bool" and cond_type != "error":
            self.errors.append(SemanticError(f"Condition in 'while' must be boolean, got '{cond_type}'", node.condition.line, node.condition.column))
        self.in_loop = True
        self._analyze_statement(node.body, expected_return_type)
        self.in_loop = False

    def _analyze_for(self, node: ForStmtNode, expected_return_type: Optional[str] = None):
        if node.init:
            if isinstance(node.init, VarDeclNode):
                self._analyze_var_decl(node.init)
            elif isinstance(node.init, ExprStmtNode):
                self._analyze_expression(node.init.expression)
            else:
                self.errors.append(SemanticError("Invalid for-init", node.init.line, node.init.column))
        if node.condition:
            cond_type = self._analyze_expression(node.condition)
            if cond_type != "bool" and cond_type != "error":
                self.errors.append(SemanticError(f"Condition in 'for' must be boolean, got '{cond_type}'", node.condition.line, node.condition.column))
        if node.update:
            self._analyze_expression(node.update)
        self.in_loop = True
        if node.body:
            self._analyze_statement(node.body, expected_return_type)
        self.in_loop = False

    def _analyze_return(self, node: ReturnStmtNode, expected_return_type: Optional[str]):
        if not self.current_function:
            self.errors.append(SemanticError("Return statement outside function", node.line, node.column))
            return
        if node.value:
            value_type = self._analyze_expression(node.value)
            if value_type == "error":
                return
            if not is_compatible(self.current_function.return_type, value_type):
                self.errors.append(SemanticError(
                    f"Return type mismatch: expected '{self.current_function.return_type}', got '{value_type}'",
                    node.line, node.column
                ))
        else:
            # return без значения
            if self.current_function.return_type != "void":
                self.errors.append(SemanticError(
                    f"Non-void function '{self.current_function.name}' must return a value",
                    node.line, node.column
                ))

    def _analyze_global_initializer(self, node: VarDeclNode):
        # Аналогично локальной переменной, но без создания новой области
        init_type = self._analyze_expression(node.initializer)
        if init_type == "error":
            return
        if not is_compatible(node.type_name, init_type):
            self.errors.append(SemanticError(
                f"Global variable initializer type mismatch: expected '{node.type_name}', got '{init_type}'",
                node.line, node.column
            ))