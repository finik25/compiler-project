from typing import List, Dict, Set, Tuple
from src.ir.ir_instructions import FunctionIR, BasicBlock, Instruction, Operand, OperandType

def compute_live_vars(func: FunctionIR) -> Dict[int, Tuple[Set[int], Set[int]]]:
    blocks = func.blocks
    num_blocks = len(blocks)

    # Индексы successor'ов
    succ_indices = []
    for block in blocks:
        indices = [blocks.index(succ) for succ in block.successors if succ in blocks]
        succ_indices.append(indices)

    defs = [set() for _ in range(num_blocks)]
    uses = [set() for _ in range(num_blocks)]

    for idx, block in enumerate(blocks):
        for instr in block.instructions:
            if instr.dest and instr.dest.kind == OperandType.TEMP:
                defs[idx].add(instr.dest.value)
            for op in [instr.src1, instr.src2] + instr.args:
                if op and op.kind == OperandType.TEMP:
                    uses[idx].add(op.value)

    live_in = [set() for _ in range(num_blocks)]
    live_out = [set() for _ in range(num_blocks)]

    changed = True
    while changed:
        changed = False
        for idx in range(num_blocks):
            new_out = set()
            for succ_idx in succ_indices[idx]:
                new_out.update(live_in[succ_idx])
            if new_out != live_out[idx]:
                live_out[idx] = new_out
                changed = True

            new_in = uses[idx].union(live_out[idx].difference(defs[idx]))
            if new_in != live_in[idx]:
                live_in[idx] = new_in
                changed = True

    return {i: (live_in[i], live_out[i]) for i in range(num_blocks)}