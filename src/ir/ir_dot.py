"""Генерация графа потока управления (CFG) в формате Graphviz DOT."""
from typing import List
from src.ir.ir_instructions import ProgramIR, FunctionIR, BasicBlock


class IRDotGenerator:
    """Генератор DOT для CFG."""

    def generate(self, program: ProgramIR) -> str:
        """Возвращает строку в формате DOT для всего ProgramIR."""
        lines = ['digraph CFG {', '  node [shape=box, fontname="Courier"];']
        for func in program.functions:
            lines.extend(self._generate_function(func))
        lines.append('}')
        return '\n'.join(lines)

    def _generate_function(self, func: FunctionIR) -> List[str]:
        lines = []
        # Подграф для функции (для группировки)
        lines.append(f'  subgraph cluster_{func.name} {{')
        lines.append(f'    label = "{func.name}";')
        lines.append(f'    style = rounded;')
        for block in func.blocks:
            # Узел: метка с инструкциями
            label = self._block_label(block)
            lines.append(f'    {block.label} [label="{label}"];')
        for block in func.blocks:
            for succ in block.successors:
                lines.append(f'    {block.label} -> {succ.label};')
        lines.append('  }')
        return lines

    def _block_label(self, block: BasicBlock) -> str:
        """Формирует многострочную метку для блока."""
        lines = [block.label + ":"]
        for instr in block.instructions:
            # Экранируем кавычки и спецсимволы для DOT
            instr_str = str(instr).replace('"', '\\"')
            lines.append(instr_str)
        # Объединяем строки с \n
        return "\\n".join(lines)