from typing import List
from src.ir.ir_instructions import ProgramIR, FunctionIR, BasicBlock, Instruction


class IRPrinter:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def print_program(self, program: ProgramIR) -> str:
        lines = []
        for func in program.functions:
            lines.extend(self.print_function(func))
            lines.append("")
        return "\n".join(lines)

    def print_function(self, func: FunctionIR) -> List[str]:
        lines = []
        params_str = ", ".join(func.parameters)
        lines.append(f"function {func.name}: {func.return_type} ({params_str})")

        if self.verbose and func.var_types:
            lines.append("  locals:")
            for var, typ in func.var_types.items():
                lines.append(f"    {var}: {typ}")

        for block in func.blocks:
            lines.append(f"  {block.label}:")
            for instr in block.instructions:
                lines.append(f"    {instr}")
        return lines