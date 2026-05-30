from typing import List, Dict, Set, Tuple
from src.ir.ir_instructions import Instruction, BasicBlock, Operand, OperandType

class LiveInterval:
    """Интервал жизни временной переменной внутри базового блока."""
    def __init__(self, temp_index: int, start: int, end: int):
        self.temp = temp_index
        self.start = start   # индекс инструкции, где определена
        self.end = end       # индекс последнего использования (включительно)

def compute_live_intervals(block: BasicBlock) -> List[LiveInterval]:
    """
    Вычисляет интервалы жизни для каждой временной переменной в пределах одного блока.
    Возвращает список LiveInterval.
    """
    # Проход 1: определить для каждой инструкции, какие temp используются и определяются
    uses: Dict[int, Set[int]] = {}   # индекс инструкции -> set temp_index
    defs: Dict[int, Set[int]] = {}   # индекс инструкции -> set temp_index
    all_temps = set()

    for idx, instr in enumerate(block.instructions):
        uses[idx] = set()
        defs[idx] = set()

        def add_operand(op: Operand):
            if op and op.kind == OperandType.TEMP:
                all_temps.add(op.value)
                uses[idx].add(op.value)

        # Обработка разных типов инструкций
        if instr.opcode.value in ('MOVE', 'LOAD'):
            if instr.dest and instr.dest.kind == OperandType.TEMP:
                defs[idx].add(instr.dest.value)
            if instr.src1:
                add_operand(instr.src1)
        elif instr.opcode.value in ('ADD', 'SUB', 'MUL', 'DIV', 'MOD', 'AND', 'OR', 'XOR',
                                    'CMP_EQ', 'CMP_NE', 'CMP_LT', 'CMP_LE', 'CMP_GT', 'CMP_GE'):
            if instr.dest and instr.dest.kind == OperandType.TEMP:
                defs[idx].add(instr.dest.value)
            add_operand(instr.src1)
            add_operand(instr.src2)
        elif instr.opcode.value in ('JUMP_IF', 'JUMP_IF_NOT'):
            add_operand(instr.src1)
        elif instr.opcode.value == 'CALL':
            if instr.dest and instr.dest.kind == OperandType.TEMP:
                defs[idx].add(instr.dest.value)
            for arg in instr.args:
                add_operand(arg)
        # RETURN, JUMP, LABEL, PARAM, PHI игнорируем (в RETURN src1 может быть temp)
        elif instr.opcode.value == 'RETURN':
            add_operand(instr.src1)

    # Проход 2: для каждого temp определить start (первое определение) и end (последнее использование)
    intervals = []
    for temp in all_temps:
        start = None
        end = -1
        for idx in range(len(block.instructions)):
            if temp in defs[idx]:
                start = idx
            if temp in uses[idx]:
                end = idx
        if start is not None:
            intervals.append(LiveInterval(temp, start, end))
    return intervals