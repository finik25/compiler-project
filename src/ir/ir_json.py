import json
from typing import Any, Dict, List
from src.ir.ir_instructions import ProgramIR, FunctionIR, BasicBlock, Instruction, Operand, OperandType, Opcode

class IRJSONGenerator:
    def generate(self, program: ProgramIR, indent: int = 2) -> str:
        return json.dumps(self._program_to_dict(program), indent=indent, ensure_ascii=False)

    def _program_to_dict(self, program: ProgramIR) -> Dict[str, Any]:
        return {
            "functions": [self._function_to_dict(f) for f in program.functions]
        }

    def _function_to_dict(self, func: FunctionIR) -> Dict[str, Any]:
        return {
            "name": func.name,
            "return_type": func.return_type,
            "parameters": func.parameters,
            "var_types": func.var_types,
            "temp_counter": func.temp_counter,
            "blocks": [self._block_to_dict(b) for b in func.blocks]
        }

    def _block_to_dict(self, block: BasicBlock) -> Dict[str, Any]:
        return {
            "label": block.label,
            "instructions": [self._instruction_to_dict(instr) for instr in block.instructions],
            "predecessors": [p.label for p in block.predecessors],
            "successors": [s.label for s in block.successors]
        }

    def _instruction_to_dict(self, instr: Instruction) -> Dict[str, Any]:
        d = {"opcode": instr.opcode.value}
        if instr.dest:
            d["dest"] = self._operand_to_dict(instr.dest)
        if instr.src1:
            d["src1"] = self._operand_to_dict(instr.src1)
        if instr.src2:
            d["src2"] = self._operand_to_dict(instr.src2)
        if instr.label:
            d["label"] = instr.label
        if instr.args:
            d["args"] = [self._operand_to_dict(a) for a in instr.args]
        if instr.comment:
            d["comment"] = instr.comment
        return d

    def _operand_to_dict(self, op: Operand) -> Dict[str, Any]:
        return {
            "kind": op.kind.value,
            "value": op.value,
            "type": op.type_name
        }