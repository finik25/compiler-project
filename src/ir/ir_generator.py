"""Генерация IR из декорированного AST."""
from typing import Dict, List, Optional
from src.parser.ast import *
from src.semantic.symbol_table import SymbolTable, Symbol, SymbolKind
from src.ir.ir_instructions import *
from src.lexer.token import TokenType


class IRGenerator:
    def __init__(self, symbol_table: SymbolTable):
        self.globals: Dict[str, Tuple[str, Optional[int]]] = {}
        self.symbol_table = symbol_table
        self.current_function: Optional[FunctionIR] = None
        self.program_ir = ProgramIR(functions=[])
        self._current_block: Optional[BasicBlock] = None
        self._loop_stack: List[str] = []

    def generate(self, program: ProgramNode) -> ProgramIR:
        self.globals = {}
        for decl in program.declarations:
            if isinstance(decl, VarDeclNode):
                self._register_global(decl)
        for decl in program.declarations:
            if isinstance(decl, FunctionDeclNode):
                self._gen_function(decl)
        return self.program_ir

    def _register_global(self, node: VarDeclNode):
        init_val = None
        if node.initializer and isinstance(node.initializer, LiteralExprNode):
            init_val = node.initializer.value
        self.globals[node.name] = (node.type_name, init_val)

    def _add_block(self, label: str) -> BasicBlock:
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
        if not block.instructions:
            return False
        last = block.instructions[-1]
        return last.opcode in (Opcode.RETURN, Opcode.JUMP, Opcode.JUMP_IF, Opcode.JUMP_IF_NOT,
                               Opcode.BR_EQ, Opcode.BR_NE, Opcode.BR_LT, Opcode.BR_LE,
                               Opcode.BR_GT, Opcode.BR_GE, Opcode.BR_ULT, Opcode.BR_ULE,
                               Opcode.BR_UGT, Opcode.BR_UGE)

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
        func_ir.var_map = {}
        entry_block = self._add_block("entry")
        self._set_current_block(entry_block)

        for param in node.parameters:
            func_ir.var_types[param.name] = param.type_name
            temp = func_ir.new_temp(param.type_name)
            func_ir.var_map[param.name] = temp

        if node.body:
            self._gen_statement(node.body, func_ir.return_type)

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

        self._build_cfg(func_ir)
        self.current_function = None
        self._current_block = None

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
                    self.current_function.var_map[node.name] = value
                else:
                    temp = self.current_function.new_temp(node.type_name)
                    self._emit(Instruction.move(temp, value))
                    self.current_function.var_map[node.name] = temp
            else:
                temp = self.current_function.new_temp(node.type_name)
                self._emit(Instruction.move(temp, Operand.const(0, node.type_name)))
                self.current_function.var_map[node.name] = temp

    # ---------- Прямые условные переходы для реляционных выражений ----------
    def _gen_cond_branch(self, expr: ExpressionNode, true_label: str, false_label: str) -> bool:
        """
        Генерирует прямой условный переход для простого реляционного выражения.
        Возвращает True, если переход сгенерирован, иначе False.
        """
        if not isinstance(expr, BinaryExprNode):
            return False
        op = expr.operator
        if op not in (TokenType.LT, TokenType.LE, TokenType.GT, TokenType.GE,
                      TokenType.EQ, TokenType.NE):
            return False

        left = self._gen_expression(expr.left)
        right = self._gen_expression(expr.right)
        if left is None or right is None:
            return False

        # Определяем беззнаковость
        is_unsigned = (expr.left.type_annotation == "unsigned int" or
                       expr.right.type_annotation == "unsigned int")

        # Выбираем опкод
        br_op = None
        if op == TokenType.LT:
            br_op = Opcode.BR_ULT if is_unsigned else Opcode.BR_LT
        elif op == TokenType.LE:
            br_op = Opcode.BR_ULE if is_unsigned else Opcode.BR_LE
        elif op == TokenType.GT:
            br_op = Opcode.BR_UGT if is_unsigned else Opcode.BR_GT
        elif op == TokenType.GE:
            br_op = Opcode.BR_UGE if is_unsigned else Opcode.BR_GE
        elif op == TokenType.EQ:
            br_op = Opcode.BR_EQ
        elif op == TokenType.NE:
            br_op = Opcode.BR_NE

        if br_op is None:
            return False

        # Генерируем BR_* с переходом на true_label
        self._emit(Instruction(opcode=br_op, src1=left, src2=right, label=true_label,
                               comment=f"if {expr}"))
        # После BR_* безусловный переход на false_label
        self._emit(Instruction.jump(false_label))
        return True

    def _gen_condition(self, expr: ExpressionNode, true_label: str, false_label: str) -> None:
        """Генерирует код для условия, переходящий на true_label при истинности, иначе на false_label."""
        # Логические операторы с коротким замыканием
        if isinstance(expr, BinaryExprNode) and expr.operator in (TokenType.AND, TokenType.OR):
            self._gen_logical_condition(expr, true_label, false_label)
            return
        # Унарное отрицание
        if isinstance(expr, UnaryExprNode) and expr.operator == TokenType.NOT:
            self._gen_condition(expr.operand, false_label, true_label)
            return
        # Прямой переход для реляционных выражений
        if self._gen_cond_branch(expr, true_label, false_label):
            return
        # Общий случай: вычисляем значение и проверяем ноль
        val = self._gen_expression(expr)
        self._emit(Instruction.jump_if_not(val, false_label))
        self._emit(Instruction.jump(true_label))

    def _gen_logical_condition(self, expr: BinaryExprNode, true_label: str, false_label: str) -> None:
        """Генерирует короткое замыкание для && и ||."""
        if expr.operator == TokenType.AND:
            next_label = self.current_function.new_label("and_next")
            self._gen_condition(expr.left, next_label, false_label)
            # Создаём блок для правой части И переключаемся на него
            self._add_block(next_label)
            self._set_current_block(self.current_function.get_block(next_label))
            self._gen_condition(expr.right, true_label, false_label)
        else:  # OR
            next_label = self.current_function.new_label("or_next")
            self._gen_condition(expr.left, true_label, next_label)
            self._add_block(next_label)
            self._set_current_block(self.current_function.get_block(next_label))
            self._gen_condition(expr.right, true_label, false_label)

    def _gen_if(self, node: IfStmtNode, expected_return_type: Optional[str] = None):
        then_label = self.current_function.new_label("then")
        else_label = self.current_function.new_label("else") if node.else_branch else None
        end_label = self.current_function.new_label("endif")

        self._gen_condition(node.condition, then_label, else_label or end_label)

        self._add_block(then_label)
        self._set_current_block(self.current_function.get_block(then_label))
        self._gen_statement(node.then_branch, expected_return_type)
        if not self._block_ends_with_terminator(self._current_block):
            self._emit(Instruction.jump(end_label))

        if node.else_branch:
            self._add_block(else_label)
            self._set_current_block(self.current_function.get_block(else_label))
            self._gen_statement(node.else_branch, expected_return_type)
            if not self._block_ends_with_terminator(self._current_block):
                self._emit(Instruction.jump(end_label))

        self._add_block(end_label)
        self._set_current_block(self.current_function.get_block(end_label))

    def _gen_while(self, node: WhileStmtNode, expected_return_type: Optional[str] = None):
        loop_label = self.current_function.new_label("loop")
        end_label = self.current_function.new_label("endwhile")
        body_label = self.current_function.new_label("body")

        cond_block = self._add_block(loop_label)
        self._set_current_block(cond_block)
        self._gen_condition(node.condition, body_label, end_label)

        self._add_block(body_label)
        self._set_current_block(self.current_function.get_block(body_label))
        self._gen_statement(node.body, expected_return_type)
        self._emit(Instruction.jump(loop_label))

        self._add_block(end_label)
        self._set_current_block(self.current_function.get_block(end_label))

    def _gen_for(self, node: ForStmtNode, expected_return_type: Optional[str] = None):
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

        cond_block = self._add_block(loop_label)
        self._set_current_block(cond_block)
        if node.condition:
            self._gen_condition(node.condition, body_label, end_label)
        else:
            # Если нет условия, бесконечный цикл
            self._emit(Instruction.jump(body_label))

        body_block = self._add_block(body_label)
        self._set_current_block(body_block)
        self._gen_statement(node.body, expected_return_type)

        step_block = self._add_block(step_label)
        self._set_current_block(step_block)
        if node.update:
            self._gen_expression(node.update)
        self._emit(Instruction.jump(loop_label))

        self._add_block(end_label)
        self._set_current_block(self.current_function.get_block(end_label))

    def _gen_return(self, node: ReturnStmtNode):
        if node.value:
            val = self._gen_expression(node.value)
            self._emit(Instruction.ret(val))
        else:
            self._emit(Instruction.ret())

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
                is_unsigned = sym.type_name == "unsigned int"
                return Operand.symbol(expr.name, sym.type_name, is_unsigned=is_unsigned)
            raise RuntimeError(f"Undeclared variable {expr.name}")

        elif isinstance(expr, BinaryExprNode):
            if expr.operator in (TokenType.AND, TokenType.OR):
                return self._gen_logical_expr(expr)
            left = self._gen_expression(expr.left)
            right = self._gen_expression(expr.right)
            dest = self.current_function.new_temp(expr.type_annotation)
            op_map = {
                TokenType.PLUS: Opcode.ADD,
                TokenType.MINUS: Opcode.SUB,
                TokenType.STAR: Opcode.MUL,
                TokenType.SLASH: Opcode.DIV,
                TokenType.PERCENT: Opcode.MOD,
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
            # Для сравнений определяем беззнаковость
            if op in (Opcode.CMP_EQ, Opcode.CMP_NE, Opcode.CMP_LT, Opcode.CMP_LE, Opcode.CMP_GT, Opcode.CMP_GE):
                is_unsigned = (expr.left.type_annotation == "unsigned int" or expr.right.type_annotation == "unsigned int")
            else:
                is_unsigned = (expr.type_annotation == "unsigned int")
            self._emit(Instruction.binary(op, dest, left, right, is_unsigned=is_unsigned))
            return dest

        elif isinstance(expr, UnaryExprNode):
            operand = self._gen_expression(expr.operand)
            if expr.operator in (TokenType.INC_OP, TokenType.DEC_OP):
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

    def _gen_logical_expr(self, expr: BinaryExprNode) -> Operand:
        """Генерирует код для логического выражения && или ||, возвращая значение (0/1)."""
        dest = self.current_function.new_temp("bool")
        true_label = self.current_function.new_label("logical_true")
        false_label = self.current_function.new_label("logical_false")
        end_label = self.current_function.new_label("logical_end")
        zero = Operand.const(0, "bool")
        one = Operand.const(1, "bool")
        self._emit(Instruction.move(dest, zero))
        if expr.operator == TokenType.AND:
            # Короткая реализация через условные переходы
            left_val = self._gen_expression(expr.left)
            self._emit(Instruction.jump_if_not(left_val, end_label))
            right_val = self._gen_expression(expr.right)
            self._emit(Instruction.jump_if_not(right_val, end_label))
            self._emit(Instruction.move(dest, one))
        else:  # OR
            left_val = self._gen_expression(expr.left)
            self._emit(Instruction.jump_if_not(left_val, false_label))
            self._emit(Instruction.move(dest, one))
            self._emit(Instruction.jump(end_label))
            self._add_block(false_label)
            right_val = self._gen_expression(expr.right)
            self._emit(Instruction.jump_if_not(right_val, end_label))
            self._emit(Instruction.move(dest, one))
        self._emit(Instruction.jump(end_label))
        self._add_block(end_label)
        return dest

    def _build_cfg(self, func: FunctionIR):
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
                if i + 1 < len(func.blocks):
                    targets.append(func.blocks[i+1].label)
            elif last.opcode in (Opcode.BR_EQ, Opcode.BR_NE, Opcode.BR_LT, Opcode.BR_LE,
                                 Opcode.BR_GT, Opcode.BR_GE, Opcode.BR_ULT, Opcode.BR_ULE,
                                 Opcode.BR_UGT, Opcode.BR_UGE):
                targets.append(last.label)
                # После BR_* всегда следует JUMP на false_label, поэтому добавляем его
                if i + 1 < len(func.blocks):
                    targets.append(func.blocks[i+1].label)
            elif last.opcode == Opcode.RETURN:
                targets = []
            else:
                if i + 1 < len(func.blocks):
                    targets.append(func.blocks[i+1].label)

            for t in targets:
                if t in block_map:
                    succ = block_map[t]
                    block.successors.append(succ)
                    succ.predecessors.append(block)