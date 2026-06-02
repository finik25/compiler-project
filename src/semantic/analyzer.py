from typing import List, Optional

from src.ir import Instruction, Opcode, Operand
from src.parser.ast import *
from src.semantic.symbol_table import SymbolTable, Symbol, SymbolKind
from src.semantic.type_system import is_compatible, get_binary_result_type, get_unary_result_type, size_of
from src.semantic.errors import SemanticError
from src.lexer.token import TokenType


class SemanticAnalyzer:
    def __init__(self):
        self.symbol_table = SymbolTable()
        self.errors = []
        self.current_function = None
        self.in_loop = False
        self._register_runtime_functions()   # <-- добавляем

    def analyze(self, program: ProgramNode):
        # Первый проход: регистрация глобальных объявлений
        for decl in program.declarations:
            if isinstance(decl, FunctionDeclNode):
                self._register_function(decl)
            elif isinstance(decl, StructDeclNode):
                self._register_struct(decl)
            elif isinstance(decl, VarDeclNode):
                self._register_global_variable(decl)
            elif isinstance(decl, ExternDeclNode):  # <-- новое
                self._register_extern_function(decl)

        # Второй проход: анализ инициализаторов глобальных переменных (вывод типов для var)
        for decl in program.declarations:
            if isinstance(decl, VarDeclNode) and decl.initializer:
                self._analyze_global_initializer(decl)

        # Третий проход: анализ тел функций
        for decl in program.declarations:
            if isinstance(decl, FunctionDeclNode):
                self._analyze_function(decl)

        return self.symbol_table, self.errors

    def _register_extern_function(self, node: ExternDeclNode):
        # Если функция уже есть во встроенных (runtime), не добавляем повторно
        builtins = {"malloc", "free", "print_int", "print_char", "exit", "printf", "scanf"}
        if node.name in builtins:
            # Просто игнорируем, т.к. уже зарегистрирована в _register_runtime_functions
            return
        existing = self.symbol_table.lookup(node.name)
        if existing:
            self.errors.append(SemanticError(f"Duplicate function '{node.name}'", node.line, node.column))
            return
        existing = self.symbol_table.lookup(node.name)
        if existing:
            self.errors.append(SemanticError(f"Duplicate function '{node.name}'", node.line, node.column))
            return
        # Создаём символ с флагом is_external = True
        func_sym = Symbol(node.name, SymbolKind.FUNCTION, node.return_type, node.line, node.column,
                          params=[], return_type=node.return_type,
                          is_external=True, is_variadic=(node.name in ('printf', 'scanf')))
        # Заполняем параметры (типы и имена)
        for param in node.parameters:
            param_sym = Symbol(param.name, SymbolKind.PARAMETER, param.type_name, param.line, param.column)
            func_sym.params.append(param_sym)
        self.symbol_table.insert(node.name, func_sym)

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
        # Для var временно сохраняем тип "var", позже выведем из инициализатора
        # Передаём array_size (0 если не массив)
        array_size = node.array_size if node.array_size is not None else 0
        var_sym = Symbol(node.name, SymbolKind.VARIABLE, node.type_name, node.line, node.column,
                         array_size=array_size)
        self.symbol_table.insert(node.name, var_sym)

    def _register_runtime_functions(self):
        """Регистрирует встроенные функции runtime (print_int, exit, print_char)."""
        # print_int: void (int)
        print_int_sym = Symbol("print_int", SymbolKind.FUNCTION, "void", 0, 0)
        print_int_sym.params = [Symbol("value", SymbolKind.PARAMETER, "int", 0, 0)]
        self.symbol_table.insert("print_int", print_int_sym)

        # exit: void (int)
        exit_sym = Symbol("exit", SymbolKind.FUNCTION, "void", 0, 0)
        exit_sym.params = [Symbol("code", SymbolKind.PARAMETER, "int", 0, 0)]
        self.symbol_table.insert("exit", exit_sym)

        # print_char: void (int)
        print_char_sym = Symbol("print_char", SymbolKind.FUNCTION, "void", 0, 0)
        print_char_sym.params = [Symbol("ch", SymbolKind.PARAMETER, "int", 0, 0)]
        self.symbol_table.insert("print_char", print_char_sym)

        # printf: int (char*, ...)
        printf_sym = Symbol("printf", SymbolKind.FUNCTION, "int", 0, 0)
        printf_sym.params = [Symbol("format", SymbolKind.PARAMETER, "char*", 0, 0)]
        printf_sym.is_variadic = True
        self.symbol_table.insert("printf", printf_sym)

        # scanf: int (char*, ...)
        scanf_sym = Symbol("scanf", SymbolKind.FUNCTION, "int", 0, 0)
        scanf_sym.params = [Symbol("format", SymbolKind.PARAMETER, "char*", 0, 0)]
        scanf_sym.is_variadic = True
        self.symbol_table.insert("scanf", scanf_sym)

        # malloc: void* (int)
        malloc_sym = Symbol("malloc", SymbolKind.FUNCTION, "void*", 0, 0)
        malloc_sym.params = [Symbol("size", SymbolKind.PARAMETER, "int", 0, 0)]
        self.symbol_table.insert("malloc", malloc_sym)

        # free: void (void*)
        free_sym = Symbol("free", SymbolKind.FUNCTION, "void", 0, 0)
        free_sym.params = [Symbol("ptr", SymbolKind.PARAMETER, "void*", 0, 0)]
        self.symbol_table.insert("free", free_sym)

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
                node.type_name = final_type

        # Обработка объявления массива
        if node.array_size is not None:
            if node.array_size <= 0:
                self.errors.append(
                    SemanticError(f"Array size must be positive, got {node.array_size}", node.line, node.column))
                return
            # Для глобальных массивов пока разрешаем только константный размер (уже есть)
            # Проверка инициализатора: списков пока нет, но можно присваивать только отдельные элементы позже
            if node.initializer:
                self.errors.append(
                    SemanticError("Array initialization with list is not supported yet", node.line, node.column))
            # Создаём символ с array_size
            var_sym = Symbol(node.name, SymbolKind.VARIABLE, node.type_name, node.line, node.column,
                             array_size=node.array_size)
            # Для массива тип переменной в таблице – это тип элемента, а размер хранится отдельно
            # Но для совместимости с существующим кодом, оставляем type_name = node.type_name
            self.symbol_table.insert(node.name, var_sym)
            # Также запомним, что это массив, чтобы при обращении по имени возвращать адрес (а не значение)
            # Эту информацию можно получить через var_sym.array_size > 0
            return
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
                error_sym = Symbol(expr.name, SymbolKind.VARIABLE, "error", expr.line, expr.column)
                self.symbol_table.insert(expr.name, error_sym)
                self.errors.append(SemanticError(f"Undeclared identifier '{expr.name}'", expr.line, expr.column))
                expr.type_annotation = "error"
                return "error"
            expr.symbol = sym
            # Если это массив, возвращаем тип указателя на элемент
            if sym.array_size > 0:
                expr.type_annotation = sym.type_name + "*"
            else:
                expr.type_annotation = sym.type_name
            return expr.type_annotation

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

        elif isinstance(expr, AddressOfExprNode):
            operand_type = self._analyze_expression(expr.operand)
            if operand_type == "error":
                expr.type_annotation = "error"
                return "error"
            # Проверка: операнд должен быть переменной (IdentifierExprNode)
            if not isinstance(expr.operand, IdentifierExprNode):
                self.errors.append(SemanticError(
                    f"Address-of operator '&' can only be applied to variables, not to expression of type '{operand_type}'",
                    expr.line, expr.column))
                expr.type_annotation = "error"
                return "error"
            result_type = operand_type + "*"
            expr.type_annotation = result_type
            return result_type

        elif isinstance(expr, DerefExprNode):
            operand_type = self._analyze_expression(expr.operand)
            if operand_type == "error":
                expr.type_annotation = "error"
                return "error"
            if not operand_type.endswith("*"):
                self.errors.append(SemanticError(
                    f"Indirection operator '*' can only be applied to pointer types, got '{operand_type}'",
                    expr.line, expr.column))
                expr.type_annotation = "error"
                return "error"
            result_type = operand_type[:-1]  # удаляем '*'
            expr.type_annotation = result_type
            return result_type
        elif isinstance(expr, ArrayAccessExprNode):
            array_type = self._analyze_expression(expr.array)
            index_type = self._analyze_expression(expr.index)
            if array_type == "error" or index_type == "error":
                expr.type_annotation = "error"
                return "error"
            if index_type not in ("int", "unsigned int"):
                self.errors.append(
                    SemanticError(f"Array index must be integer, got '{index_type}'", expr.line, expr.column))
                expr.type_annotation = "error"
                return "error"
            # Если array_type - указатель или массив
            if array_type.endswith("*") or (isinstance(expr.array,
                                                       IdentifierExprNode) and expr.array.symbol and expr.array.symbol.array_size > 0):
                element_type = array_type[:-1] if array_type.endswith("*") else array_type
                expr.type_annotation = element_type
                return element_type
            else:
                self.errors.append(
                    SemanticError(f"Can only index array or pointer, got '{array_type}'", expr.line, expr.column))
                expr.type_annotation = "error"
                return "error"
        elif isinstance(expr, CallExprNode):
            sym = self.symbol_table.lookup(expr.callee)
            if not sym or sym.kind != SymbolKind.FUNCTION:
                self.errors.append(SemanticError(f"Call to undeclared function '{expr.callee}'", expr.line, expr.column))
                expr.type_annotation = "error"
                return "error"
            expr.function_symbol = sym
            # Проверка аргументов (с учётом error propagation)
            if len(expr.arguments) < len(sym.params):
                if sym.is_variadic:
                    msg = f"Argument count mismatch for function '{expr.callee}': expected at least {len(sym.params)}, got {len(expr.arguments)}"
                else:
                    msg = f"Argument count mismatch for function '{expr.callee}': expected {len(sym.params)}, got {len(expr.arguments)}"
                self.errors.append(SemanticError(msg, expr.line, expr.column))
            elif not sym.is_variadic and len(expr.arguments) > len(sym.params):
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
            target_node = expr.target
            # Определяем тип левой части
            if isinstance(target_node, IdentifierExprNode):
                target_sym = self.symbol_table.lookup(target_node.name)
                if not target_sym:
                    error_sym = Symbol(target_node.name, SymbolKind.VARIABLE, "error", target_node.line,
                                       target_node.column)
                    self.symbol_table.insert(target_node.name, error_sym)
                    self.errors.append(
                        SemanticError(f"Assignment to undeclared variable '{target_node.name}'", target_node.line,
                                      target_node.column))
                    expr.type_annotation = "error"
                    return "error"
                target_type = target_sym.type_name
            elif isinstance(target_node, ArrayAccessExprNode):
                target_type = self._analyze_expression(target_node)
                if target_type == "error":
                    expr.type_annotation = "error"
                    return "error"
            elif isinstance(target_node, DerefExprNode):
                # *ptr = value
                ptr_type = self._analyze_expression(target_node.operand)
                if ptr_type == "error":
                    target_type = "error"
                elif ptr_type.endswith("*"):
                    target_type = ptr_type[:-1]  # удаляем последнюю '*', получаем базовый тип
                else:
                    self.errors.append(
                        SemanticError(f"Cannot dereference non-pointer type '{ptr_type}'", target_node.line,
                                      target_node.column))
                    target_type = "error"
            else:
                self.errors.append(SemanticError(f"Invalid left-hand side in assignment", expr.line, expr.column))
                expr.type_annotation = "error"
                return "error"
            # Анализируем правую часть
            right_type = self._analyze_expression(expr.value)
            if right_type == "error" or target_type == "error":
                expr.type_annotation = "error"
                return "error"
            # Проверка совместимости типов
            if not is_compatible(target_type, right_type):
                self.errors.append(SemanticError(
                    f"Assignment type mismatch: left side is '{target_type}', expression is '{right_type}'",
                    expr.value.line, expr.value.column
                ))
                expr.type_annotation = "error"
                return "error"
            # Составные присваивания – требуют числового типа
            if expr.operator != TokenType.ASSIGN:
                if target_type not in ("int", "float", "unsigned int"):
                    self.errors.append(SemanticError(
                        f"Compound assignment operator requires numeric type, got '{target_type}'",
                        expr.line, expr.column
                    ))
                    expr.type_annotation = "error"
                    return "error"
            expr.type_annotation = target_type
            return target_type

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
        # Анализируем инициализатор
        init_type = self._analyze_expression(node.initializer)
        if init_type == "error":
            return

        sym = self.symbol_table.lookup(node.name)
        if not sym:
            self.errors.append(SemanticError(f"Global variable '{node.name}' not found", node.line, node.column))
            return

        if node.type_name == "var":
            if init_type == "error":
                return
            # Выводим тип
            sym.type_name = init_type
            node.type_name = init_type
        else:
            if not is_compatible(node.type_name, init_type):
                self.errors.append(SemanticError(
                    f"Global variable initializer type mismatch: expected '{node.type_name}', got '{init_type}'",
                    node.line, node.column
                ))