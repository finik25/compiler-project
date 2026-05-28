"""Генерация IR из декорированного AST."""

from typing import Dict, List, Optional
from src.parser.ast import *
from src.semantic.symbol_table import SymbolTable, Symbol, SymbolKind
from src.ir.ir_instructions import *
from src.lexer.token import TokenType


class IRGenerator:
    """Преобразует AST в трёхадресный код (IR) с базовыми блоками."""

    def __init__(self, symbol_table: SymbolTable):
        self.symbol_table = symbol_table
        self.current_function: Optional[FunctionIR] = None
        self.program_ir = ProgramIR(functions=[])
        self._current_block: Optional[BasicBlock] = None
        self._loop_stack: List[str] = []  # для break/continue (пока не используется)

    def generate(self, program: ProgramNode) -> ProgramIR:
        """Главный метод: обход AST и создание ProgramIR."""
        for decl in program.declarations:
            if isinstance(decl, FunctionDeclNode):
                self._gen_function(decl)
        return self.program_ir

    # --------------------------------------------------------------------------
    # Вспомогательные методы
    # --------------------------------------------------------------------------
    def _add_block(self, label: str) -> BasicBlock:
        """Создаёт и добавляет блок в текущую функцию, возвращает его."""
        block = BasicBlock(label=label)
        self.current_function.add_block(block)
        return block

    def _set_current_block(self, block: BasicBlock):
        self._current_block = block

    def _emit(self, instr: Instruction):
        if self._current_block is None:
            raise RuntimeError("No current block to emit instruction")
        self._current_block.add_instruction(instr)

    def _block_ends_with_terminator(self, block: BasicBlock) -> bool:
        """Проверяет, заканчивается ли блок управляющей инструкцией."""
        if not block.instructions:
            return False
        last = block.instructions[-1]
        return last.opcode in (Opcode.RETURN, Opcode.JUMP, Opcode.JUMP_IF, Opcode.JUMP_IF_NOT)

    # --------------------------------------------------------------------------
    # Генерация функций
    # --------------------------------------------------------------------------
    def _gen_function(self, node: FunctionDeclNode):
        func_ir = FunctionIR(
            name=node.name,
            return_type=node.return_type,
            parameters=[p.name for p in node.parameters],
            blocks=[],
            var_types={}
        )
        self.current_function = func_ir
        self.program_ir.functions.append(func_ir)

        # Словарь для отображения локальных переменных на временные
        func_ir.var_map = {}

        # Входной базовый блок (фиксированная метка "entry")
        entry_block = self._add_block("entry")
        self._set_current_block(entry_block)

        # Параметры: создаём временные переменные для каждого параметра
        for param in node.parameters:
            func_ir.var_types[param.name] = param.type_name
            temp = func_ir.new_temp(param.type_name)
            func_ir.var_map[param.name] = temp

        # Генерация тела функции
        if node.body:
            self._gen_statement(node.body, func_ir.return_type)

        # Если функция не закончилась RETURN, добавим фиктивный (для void или ошибка)
        has_return = any(
            instr.opcode == Opcode.RETURN
            for block in func_ir.blocks
            for instr in block.instructions
        )
        if not has_return:
            if func_ir.return_type != "void":
                self._emit(Instruction.ret(Operand.const(0, "int")))
            else:
                self._emit(Instruction.ret())

        # Построение CFG
        self._build_cfg(func_ir)

        self.current_function = None
        self._current_block = None

    # --------------------------------------------------------------------------
    # Генерация операторов
    # --------------------------------------------------------------------------
    def _gen_statement(self, stmt: ASTNode, expected_return_type: Optional[str] = None):
        if isinstance(stmt, BlockStmtNode):
            for s in stmt.statements:
                self._gen_statement(s, expected_return_type)
        elif isinstance(stmt, ExprStmtNode):
            self._gen_expression(stmt.expression)
        elif isinstance(stmt, VarDeclNode):
            self._gen_var_decl(stmt)
        elif isinstance(stmt, IfStmtNode):
            self._gen_if(stmt, expected_return_type)
        elif isinstance(stmt, WhileStmtNode):
            self._gen_while(stmt, expected_return_type)
        elif isinstance(stmt, ForStmtNode):
            self._gen_for(stmt, expected_return_type)
        elif isinstance(stmt, ReturnStmtNode):
            self._gen_return(stmt)
        elif isinstance(stmt, EmptyStmtNode):
            pass
        else:
            raise NotImplementedError(f"Statement type not implemented: {type(stmt)}")

    def _gen_var_decl(self, node: VarDeclNode):
        if self.current_function:
            self.current_function.var_types[node.name] = node.type_name
            if node.initializer:
                value = self._gen_expression(node.initializer)
                if value and value.kind == OperandType.TEMP:
                    # Переиспользуем временную переменную
                    self.current_function.var_map[node.name] = value
                else:
                    temp = self.current_function.new_temp(node.type_name)
                    self._emit(Instruction.move(temp, value))
                    self.current_function.var_map[node.name] = temp
            else:
                # Неинициализированная переменная: инициализируем нулём
                temp = self.current_function.new_temp(node.type_name)
                self._emit(Instruction.move(temp, Operand.const(0, node.type_name)))
                self.current_function.var_map[node.name] = temp
        else:
            # Глобальная переменная – пока игнорируем
            pass

    def _gen_if(self, node: IfStmtNode, expected_return_type: Optional[str] = None):
        cond = self._gen_expression(node.condition)
        else_label = self.current_function.new_label("else") if node.else_branch else None
        end_label = self.current_function.new_label("endif")
        need_end = False  # флаг, нужен ли блок endif

        if else_label:
            self._emit(Instruction.jump_if_not(cond, else_label))
        else:
            self._emit(Instruction.jump_if_not(cond, end_label))
            need_end = True  # если нет else, то безусловный переход на endif нужен

        # Then блок
        then_label = self.current_function.new_label("then")
        then_block = self._add_block(then_label)
        self._set_current_block(then_block)
        self._gen_statement(node.then_branch, expected_return_type)
        if not self._block_ends_with_terminator(self._current_block):
            self._emit(Instruction.jump(end_label))
            need_end = True

        # Else блок (если есть)
        if node.else_branch:
            else_block = self._add_block(else_label)
            self._set_current_block(else_block)
            self._gen_statement(node.else_branch, expected_return_type)
            if not self._block_ends_with_terminator(self._current_block):
                self._emit(Instruction.jump(end_label))
                need_end = True

        # Создаём блок endif, только если он нужен
        if need_end:
            self._add_block(end_label)
            self._set_current_block(self.current_function.get_block(end_label))

    def _gen_while(self, node: WhileStmtNode, expected_return_type: Optional[str] = None):
        loop_label = self.current_function.new_label("loop")
        end_label = self.current_function.new_label("endwhile")

        # Блок условия (начало цикла)
        cond_block = self._add_block(loop_label)
        self._set_current_block(cond_block)
        cond = self._gen_expression(node.condition)
        self._emit(Instruction.jump_if_not(cond, end_label))

        # Тело цикла
        body_label = self.current_function.new_label("body")
        body_block = self._add_block(body_label)
        self._set_current_block(body_block)
        self._gen_statement(node.body, expected_return_type)
        self._emit(Instruction.jump(loop_label))

        # Блок выхода
        self._add_block(end_label)
        self._set_current_block(self.current_function.get_block(end_label))

    def _gen_for(self, node: ForStmtNode, expected_return_type: Optional[str] = None):
        # Инициализация
        if node.init:
            if isinstance(node.init, VarDeclNode):
                self._gen_var_decl(node.init)
            elif isinstance(node.init, ExprStmtNode):
                self._gen_expression(node.init.expression)
            else:
                raise NotImplementedError(f"For init type: {type(node.init)}")

        loop_label = self.current_function.new_label("for_cond")
        body_label = self.current_function.new_label("for_body")
        step_label = self.current_function.new_label("for_step")
        end_label = self.current_function.new_label("for_end")

        # Блок условия
        cond_block = self._add_block(loop_label)
        self._set_current_block(cond_block)
        if node.condition:
            cond = self._gen_expression(node.condition)
            self._emit(Instruction.jump_if_not(cond, end_label))
        # если условия нет – бесконечный цикл

        # Тело
        body_block = self._add_block(body_label)
        self._set_current_block(body_block)
        self._gen_statement(node.body, expected_return_type)

        # Шаг (update)
        step_block = self._add_block(step_label)
        self._set_current_block(step_block)
        if node.update:
            self._gen_expression(node.update)
        self._emit(Instruction.jump(loop_label))

        # Блок выхода
        self._add_block(end_label)
        self._set_current_block(self.current_function.get_block(end_label))

    def _gen_return(self, node: ReturnStmtNode):
        if node.value:
            val = self._gen_expression(node.value)
            self._emit(Instruction.ret(val))
        else:
            self._emit(Instruction.ret())

    # --------------------------------------------------------------------------
    # Генерация выражений
    # --------------------------------------------------------------------------
    def _gen_expression(self, expr: ExpressionNode) -> Optional[Operand]:
        if isinstance(expr, LiteralExprNode):
            if expr.literal_type in (TokenType.INT_LITERAL, TokenType.KW_TRUE, TokenType.KW_FALSE):
                val = expr.value
                typ = "int" if expr.literal_type == TokenType.INT_LITERAL else "bool"
                if typ == "bool":
                    val = 1 if val else 0
                return Operand.const(val, typ)
            elif expr.literal_type == TokenType.FLOAT_LITERAL:
                return Operand.const(expr.value, "float")
            elif expr.literal_type == TokenType.STRING_LITERAL:
                return Operand.const(expr.value, "string")
            else:
                raise NotImplementedError(f"Literal type {expr.literal_type}")

        elif isinstance(expr, IdentifierExprNode):
            if self.current_function and expr.name in self.current_function.var_map:
                return self.current_function.var_map[expr.name]
            sym = self.symbol_table.lookup(expr.name)
            if sym:
                return Operand.symbol(expr.name, sym.type_name)
            raise RuntimeError(f"Undeclared variable {expr.name}")

        elif isinstance(expr, BinaryExprNode):
            left = self._gen_expression(expr.left)
            right = self._gen_expression(expr.right)
            dest = self.current_function.new_temp(expr.type_annotation)
            op_map = {
                TokenType.PLUS: Opcode.ADD,
                TokenType.MINUS: Opcode.SUB,
                TokenType.STAR: Opcode.MUL,
                TokenType.SLASH: Opcode.DIV,
                TokenType.PERCENT: Opcode.MOD,
                TokenType.AND: Opcode.AND,
                TokenType.OR: Opcode.OR,
                TokenType.EQ: Opcode.CMP_EQ,
                TokenType.NE: Opcode.CMP_NE,
                TokenType.LT: Opcode.CMP_LT,
                TokenType.LE: Opcode.CMP_LE,
                TokenType.GT: Opcode.CMP_GT,
                TokenType.GE: Opcode.CMP_GE,
            }
            op = op_map.get(expr.operator)
            if op is None:
                raise NotImplementedError(f"Binary operator {expr.operator}")
            self._emit(Instruction.binary(op, dest, left, right))
            return dest

        elif isinstance(expr, UnaryExprNode):
            operand = self._gen_expression(expr.operand)
            if expr.operator in (TokenType.INC_OP, TokenType.DEC_OP):
                # префиксный ++/--
                new_val = self.current_function.new_temp(expr.type_annotation)
                if expr.operator == TokenType.INC_OP:
                    self._emit(Instruction.binary(Opcode.ADD, new_val, operand, Operand.const(1, "int")))
                else:
                    self._emit(Instruction.binary(Opcode.SUB, new_val, operand, Operand.const(1, "int")))
                self._emit(Instruction.move(operand, new_val))
                return new_val
            elif expr.operator == TokenType.MINUS:
                dest = self.current_function.new_temp(expr.type_annotation)
                self._emit(Instruction.unary(Opcode.NEG, dest, operand))
                return dest
            elif expr.operator == TokenType.NOT:
                dest = self.current_function.new_temp(expr.type_annotation)
                self._emit(Instruction.unary(Opcode.NOT, dest, operand))
                return dest
            else:
                raise NotImplementedError(f"Unary operator {expr.operator}")

        elif isinstance(expr, PostfixExprNode):
            operand = self._gen_expression(expr.operand)
            old_val = self.current_function.new_temp(expr.type_annotation)
            self._emit(Instruction.move(old_val, operand))
            new_val = self.current_function.new_temp(expr.type_annotation)
            if expr.operator == TokenType.INC_OP:
                self._emit(Instruction.binary(Opcode.ADD, new_val, operand, Operand.const(1, "int")))
            else:
                self._emit(Instruction.binary(Opcode.SUB, new_val, operand, Operand.const(1, "int")))
            self._emit(Instruction.move(operand, new_val))
            return old_val

        elif isinstance(expr, AssignmentExprNode):
            value = self._gen_expression(expr.value)
            if self.current_function and expr.target in self.current_function.var_map:
                dest = self.current_function.var_map[expr.target]
            else:
                sym = self.symbol_table.lookup(expr.target)
                if sym is None:
                    raise RuntimeError(f"Undeclared variable {expr.target}")
                dest = Operand.symbol(expr.target, sym.type_name)

            if expr.operator != TokenType.ASSIGN:
                loaded = self.current_function.new_temp(expr.value.type_annotation)
                self._emit(Instruction.load(loaded, dest))
                op_map = {
                    TokenType.ADD_ASSIGN: Opcode.ADD,
                    TokenType.SUB_ASSIGN: Opcode.SUB,
                    TokenType.MUL_ASSIGN: Opcode.MUL,
                    TokenType.DIV_ASSIGN: Opcode.DIV,
                }
                op = op_map.get(expr.operator)
                if op is None:
                    raise NotImplementedError(f"Compound assign {expr.operator}")
                temp = self.current_function.new_temp(expr.type_annotation)
                self._emit(Instruction.binary(op, temp, loaded, value))
                value = temp
            self._emit(Instruction.move(dest, value))
            return value

        elif isinstance(expr, CallExprNode):
            func_sym = self.symbol_table.lookup(expr.callee)
            if not func_sym or func_sym.kind != SymbolKind.FUNCTION:
                raise RuntimeError(f"Call to non-function {expr.callee}")
            arg_ops = [self._gen_expression(arg) for arg in expr.arguments]
            for arg in arg_ops:
                self._emit(Instruction(Opcode.PARAM, src1=arg))
            if expr.type_annotation != "void":
                dest = self.current_function.new_temp(expr.type_annotation)
                self._emit(Instruction.call(dest, expr.callee, arg_ops))
                return dest
            else:
                self._emit(Instruction.call(None, expr.callee, arg_ops))
                return None

        else:
            raise NotImplementedError(f"Expression type {type(expr)}")

    # --------------------------------------------------------------------------
    # Построение CFG (Control Flow Graph)
    # --------------------------------------------------------------------------
    def _build_cfg(self, func: FunctionIR):
        """Заполняет predecessors и successors для всех блоков функции."""
        block_map = {b.label: b for b in func.blocks}
        for i, block in enumerate(func.blocks):
            if not block.instructions:
                continue
            last = block.instructions[-1]
            targets = []
            if last.opcode == Opcode.JUMP:
                targets.append(last.label)
            elif last.opcode in (Opcode.JUMP_IF, Opcode.JUMP_IF_NOT):
                targets.append(last.label)
                # fallthrough: следующий блок в списке (если есть) тоже successor
                if i + 1 < len(func.blocks):
                    targets.append(func.blocks[i+1].label)
            elif last.opcode == Opcode.RETURN:
                targets = []
            else:
                # Если нет управляющей инструкции, следующий блок (не должно случаться)
                if i + 1 < len(func.blocks):
                    targets.append(func.blocks[i+1].label)

            for t in targets:
                if t in block_map:
                    succ = block_map[t]
                    block.successors.append(succ)
                    succ.predecessors.append(block)