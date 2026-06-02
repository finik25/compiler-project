from src.ir.ir_instructions import ProgramIR, FunctionIR, BasicBlock, Instruction, Operand, OperandType, Opcode
from typing import Set, Dict, Optional

class IROptimizer:
    def __init__(self):
        self.changed = False

    def optimize(self, program: ProgramIR) -> ProgramIR:
        self.changed = True
        while self.changed:
            self.changed = False
            for func in program.functions:
                self.optimize_function(func)
        return program

    def optimize_function(self, func: FunctionIR):
        self.constant_folding(func)
        self.constant_propagation(func)
        self.dead_code_elimination(func)
        # Можно добавить удаление недостижимых блоков
        self.remove_unreachable_blocks(func)

    # ------------------------------------------------------------
    # 1. Constant folding
    # ------------------------------------------------------------
    def constant_folding(self, func: FunctionIR):
        for block in func.blocks:
            new_instrs = []
            for instr in block.instructions:
                folded = self._fold_instruction(instr)
                if folded is not None:
                    new_instrs.append(folded)
                    self.changed = True
                else:
                    new_instrs.append(instr)
            block.instructions = new_instrs

    def _fold_instruction(self, instr: Instruction) -> Optional[Instruction]:
        # Бинарные операции
        if instr.opcode in (Opcode.ADD, Opcode.SUB, Opcode.MUL, Opcode.DIV, Opcode.MOD,
                            Opcode.AND, Opcode.OR, Opcode.XOR,
                            Opcode.CMP_EQ, Opcode.CMP_NE, Opcode.CMP_LT, Opcode.CMP_LE,
                            Opcode.CMP_GT, Opcode.CMP_GE):
            if (instr.src1 and instr.src1.kind == OperandType.CONST and
                instr.src2 and instr.src2.kind == OperandType.CONST):
                left = instr.src1.value
                right = instr.src2.value
                result = None
                if instr.opcode == Opcode.ADD:
                    result = left + right
                elif instr.opcode == Opcode.SUB:
                    result = left - right
                elif instr.opcode == Opcode.MUL:
                    result = left * right
                elif instr.opcode == Opcode.DIV:
                    # Для учебных целей – целочисленное деление
                    if right == 0:
                        return None
                    result = left // right
                elif instr.opcode == Opcode.MOD:
                    if right == 0:
                        return None
                    result = left % right
                elif instr.opcode == Opcode.AND:
                    result = left and right
                elif instr.opcode == Opcode.OR:
                    result = left or right
                elif instr.opcode == Opcode.XOR:
                    result = left ^ right
                elif instr.opcode == Opcode.CMP_EQ:
                    result = 1 if left == right else 0
                elif instr.opcode == Opcode.CMP_NE:
                    result = 1 if left != right else 0
                elif instr.opcode == Opcode.CMP_LT:
                    result = 1 if left < right else 0
                elif instr.opcode == Opcode.CMP_LE:
                    result = 1 if left <= right else 0
                elif instr.opcode == Opcode.CMP_GT:
                    result = 1 if left > right else 0
                elif instr.opcode == Opcode.CMP_GE:
                    result = 1 if left >= right else 0
                if result is not None:
                    const = Operand.const(result, instr.dest.type_name)
                    return Instruction.move(instr.dest, const)
        # Унарные операции
        if instr.opcode in (Opcode.NEG, Opcode.NOT):
            if instr.src1 and instr.src1.kind == OperandType.CONST:
                val = instr.src1.value
                if instr.opcode == Opcode.NEG:
                    result = -val
                else:  # NOT
                    result = 0 if val else 1
                const = Operand.const(result, instr.dest.type_name)
                return Instruction.move(instr.dest, const)
        return None

    # ------------------------------------------------------------
    # 2. Constant propagation
    # ------------------------------------------------------------
    def constant_propagation(self, func: FunctionIR):
        const_values = {}
        changed = False
        for block in func.blocks:
            for instr in block.instructions:
                # Запоминаем константы
                if instr.opcode == Opcode.MOVE and instr.src1.kind == OperandType.CONST:
                    if instr.dest.kind == OperandType.TEMP:
                        const_values[instr.dest.value] = instr.src1.value
                        changed = True
                # Заменяем использования
                self._replace_operands_with_const(instr, const_values)
        return changed

    def _replace_operands_with_const(self, instr: Instruction, const_map: Dict[int, int]):
        for slot in ('src1', 'src2'):
            op = getattr(instr, slot)
            if op and op.kind == OperandType.TEMP and op.value in const_map:
                new_val = const_map[op.value]
                new_op = Operand.const(new_val, op.type_name)
                setattr(instr, slot, new_op)
                self.changed = True
        # Аргументы вызовов
        for i, arg in enumerate(instr.args):
            if arg.kind == OperandType.TEMP and arg.value in const_map:
                new_val = const_map[arg.value]
                new_op = Operand.const(new_val, arg.type_name)
                instr.args[i] = new_op
                self.changed = True

    # ------------------------------------------------------------
    # 3. Dead code elimination (удаление неиспользуемых определений)
    # ------------------------------------------------------------
    def dead_code_elimination(self, func: FunctionIR):
        used = self._collect_used_temps(func)
        for block in func.blocks:
            new_instrs = []
            for instr in block.instructions:
                # Если инструкция определяет временную, которая не используется
                if (instr.dest and instr.dest.kind == OperandType.TEMP and
                    instr.dest.value not in used and
                    self._has_no_side_effects(instr)):
                    self.changed = True
                    continue  # удаляем
                new_instrs.append(instr)
            block.instructions = new_instrs

    def _collect_used_temps(self, func: FunctionIR) -> Set[int]:
        used = set()
        for block in func.blocks:
            for instr in block.instructions:
                for op in [instr.src1, instr.src2] + instr.args:
                    if op and op.kind == OperandType.TEMP:
                        used.add(op.value)
        return used

    def _has_no_side_effects(self, instr: Instruction) -> bool:
        # Инструкции, которые можно безопасно удалить, если их результат не используется
        no_effect = (Opcode.MOVE, Opcode.ADD, Opcode.SUB, Opcode.MUL, Opcode.DIV, Opcode.MOD,
                     Opcode.AND, Opcode.OR, Opcode.XOR, Opcode.NEG, Opcode.NOT,
                     Opcode.CMP_EQ, Opcode.CMP_NE, Opcode.CMP_LT, Opcode.CMP_LE,
                     Opcode.CMP_GT, Opcode.CMP_GE, Opcode.LOAD)
        return instr.opcode in no_effect

    # ------------------------------------------------------------
    # 4. Dead store elimination (store, после которого нет load)
    # ------------------------------------------------------------
    def dead_code_elimination(self, func: FunctionIR):
        used = set()
        # Сначала соберём все использования
        for block in func.blocks:
            for instr in block.instructions:
                for op in [instr.src1, instr.src2] + instr.args:
                    if op and op.kind == OperandType.TEMP:
                        used.add(op.value)
        # Теперь удалим определения, не используемые
        for block in func.blocks:
            new_instrs = []
            for instr in block.instructions:
                # Если инструкция имеет dest и это TEMP, и dest не используется
                if instr.dest and instr.dest.kind == OperandType.TEMP and instr.dest.value not in used:
                    # Проверяем, нет ли побочных эффектов
                    if instr.opcode not in (Opcode.CALL, Opcode.STORE, Opcode.RETURN):
                        continue  # пропускаем
                new_instrs.append(instr)
            block.instructions = new_instrs

    # ------------------------------------------------------------
    # 5. Удаление недостижимых базовых блоков
    # ------------------------------------------------------------
    def remove_unreachable_blocks(self, func: FunctionIR):
        # Находим все достижимые блоки, начиная с entry
        reachable = set()
        worklist = [func.blocks[0].label]
        while worklist:
            label = worklist.pop()
            if label in reachable:
                continue
            reachable.add(label)
            block = func.get_block(label)
            if block:
                for succ in block.successors:
                    if succ.label not in reachable:
                        worklist.append(succ.label)
        # Удаляем недостижимые
        new_blocks = [b for b in func.blocks if b.label in reachable]
        if len(new_blocks) != len(func.blocks):
            func.blocks = new_blocks
            self.changed = True

