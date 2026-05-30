# src/codegen/register_allocator.py

from typing import Dict, List, Set, Optional, Tuple
from src.ir.ir_instructions import FunctionIR, BasicBlock, Opcode, OperandType
from src.codegen.liveness import compute_live_intervals, LiveInterval
from src.codegen.abi import TEMP_REGS

class RegisterAllocator:
    def __init__(self, func: FunctionIR, num_regs: int = 6):
        self.func = func
        self.num_regs = min(num_regs, len(TEMP_REGS))
        self.phys_regs = TEMP_REGS[:self.num_regs]

    def allocate(self) -> Tuple[Dict[int, Optional[str]], Dict[int, bool]]:
        mapping: Dict[int, Optional[str]] = {}
        is_spilled: Dict[int, bool] = {}

        # Определяем межблочные временные
        temp_blocks: Dict[int, Set[str]] = {}
        for block in self.func.blocks:
            for instr in block.instructions:
                for op in self._collect_operands(instr):
                    if op.kind == OperandType.TEMP:
                        temp_blocks.setdefault(op.value, set()).add(block.label)

        # Принудительно спиллим временные, которые встречаются в нескольких блоках
        multi_block_temps = {temp for temp, blocks in temp_blocks.items() if len(blocks) > 1}
        for temp in multi_block_temps:
            mapping[temp] = None
            is_spilled[temp] = True

        # Для каждого блока выполняем локальную аллокацию (только для временных, которые не multi-block)
        for block in self.func.blocks:
            intervals = compute_live_intervals(block)
            # Отфильтруем интервалы для уже спиленных временных
            intervals = [iv for iv in intervals if iv.temp not in multi_block_temps]
            if not intervals:
                continue

            intervals.sort(key=lambda iv: iv.start)
            active: List[LiveInterval] = []
            reg_map: Dict[int, str] = {}

            for iv in intervals:
                # Освобождаем завершившиеся
                expired = [a for a in active if a.end < iv.start]
                for a in expired:
                    active.remove(a)
                    if a.temp in reg_map:
                        del reg_map[a.temp]

                # Пытаемся назначить свободный регистр
                assigned_reg = None
                for reg in self.phys_regs:
                    if reg not in reg_map.values():
                        assigned_reg = reg
                        break

                if assigned_reg is not None:
                    reg_map[iv.temp] = assigned_reg
                    active.append(iv)
                    active.sort(key=lambda x: x.end)
                    mapping[iv.temp] = assigned_reg
                    is_spilled[iv.temp] = False
                else:
                    # Нет свободного регистра – выбираем интервал с самым большим концом для spill
                    to_spill = max(active, key=lambda x: x.end)
                    active.remove(to_spill)
                    freed_reg = reg_map.pop(to_spill.temp)
                    # Теперь текущий интервал занимает этот регистр
                    reg_map[iv.temp] = freed_reg
                    active.append(iv)
                    active.sort(key=lambda x: x.end)
                    mapping[iv.temp] = freed_reg
                    is_spilled[iv.temp] = False
                    # Помечаем вытесненный как spill
                    mapping[to_spill.temp] = None
                    is_spilled[to_spill.temp] = True

        return mapping, is_spilled


    def _collect_operands(self, instr) -> List[Operand]:
        from src.ir.ir_instructions import Operand, OperandType, Opcode
        ops = []
        if instr.dest and instr.dest.kind == OperandType.TEMP:
            ops.append(instr.dest)
        if instr.src1 and instr.src1.kind == OperandType.TEMP:
            ops.append(instr.src1)
        if instr.src2 and instr.src2.kind == OperandType.TEMP:
            ops.append(instr.src2)
        if instr.args:
            for arg in instr.args:
                if arg.kind == OperandType.TEMP:
                    ops.append(arg)
        return ops