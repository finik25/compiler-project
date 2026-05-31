from typing import Dict, List, Set, Optional, Tuple
from src.ir.ir_instructions import FunctionIR, BasicBlock, OperandType
from src.codegen.liveness import compute_live_vars
from src.codegen.abi import TEMP_REGS

class RegisterAllocator:
    def __init__(self, func: FunctionIR, num_regs: int = 6):
        self.func = func
        self.num_regs = min(num_regs, len(TEMP_REGS))
        self.phys_regs = TEMP_REGS[:self.num_regs]

    def allocate(self) -> Tuple[Dict[int, Optional[str]], Dict[int, bool]]:
        # Анализ живых переменных – возвращает словарь индекс блока -> (live_in, live_out)
        live_info = compute_live_vars(self.func)
        blocks = self.func.blocks
        num_blocks = len(blocks)

        # Собираем всех временных
        all_temps = set()
        for block in blocks:
            for instr in block.instructions:
                for op in [instr.dest, instr.src1, instr.src2] + instr.args:
                    if op and op.kind == OperandType.TEMP:
                        all_temps.add(op.value)

        # Для каждого временного определим первый и последний блок
        first_block: Dict[int, int] = {}
        last_block: Dict[int, int] = {}
        for temp in all_temps:
            first = num_blocks
            last = -1
            for idx, block in enumerate(blocks):
                live_in, live_out = live_info[idx]
                if temp in live_in or temp in live_out:
                    first = min(first, idx)
                    last = max(last, idx)
                # также проверяем, определён ли temp в блоке
                for instr in block.instructions:
                    if instr.dest and instr.dest.kind == OperandType.TEMP and instr.dest.value == temp:
                        first = min(first, idx)
                        last = max(last, idx)
            first_block[temp] = first
            last_block[temp] = last

        # Сортируем временные по началу интервала
        sorted_temps = sorted(all_temps, key=lambda t: first_block[t])

        active: List[Tuple[int, int]] = []  # (last, temp)
        reg_assign: Dict[int, str] = {}
        reg_map: Dict[int, Optional[str]] = {}
        spill_map: Dict[int, bool] = {}

        for temp in sorted_temps:
            start = first_block[temp]
            end = last_block[temp]

            # Освобождаем регистры у тех, чей last < start
            new_active = []
            for (last_a, t) in active:
                if last_a >= start:
                    new_active.append((last_a, t))
                else:
                    if t in reg_assign:
                        del reg_assign[t]
            active = new_active

            # Пытаемся выделить свободный регистр
            allocated_reg = None
            for reg in self.phys_regs:
                if reg not in reg_assign.values():
                    allocated_reg = reg
                    break

            if allocated_reg is not None:
                reg_assign[temp] = allocated_reg
                active.append((end, temp))
                active.sort(key=lambda x: x[0])
                reg_map[temp] = allocated_reg
                spill_map[temp] = False
            else:
                # Нет свободного регистра – вытесняем интервал с максимальным концом
                to_spill = max(active, key=lambda x: x[0])[1]
                if to_spill in reg_assign:
                    freed_reg = reg_assign[to_spill]
                    del reg_assign[to_spill]
                    active.remove((last_block[to_spill], to_spill))
                    reg_assign[temp] = freed_reg
                    active.append((end, temp))
                    active.sort(key=lambda x: x[0])
                    reg_map[temp] = freed_reg
                    spill_map[temp] = False
                    reg_map[to_spill] = None
                    spill_map[to_spill] = True
                else:
                    reg_map[temp] = None
                    spill_map[temp] = True

        for temp in all_temps:
            if temp not in reg_map:
                reg_map[temp] = None
                spill_map[temp] = True

        return reg_map, spill_map