"""Intermediate Representation (IR) module for MiniCompiler."""

from src.ir.ir_instructions import (
    OperandType, Operand, Opcode, Instruction,
    BasicBlock, FunctionIR, ProgramIR
)
from src.ir.ir_printer import IRPrinter
from src.ir.ir_dot import IRDotGenerator
from src.ir.ir_generator import IRGenerator

__all__ = [
    "OperandType", "Operand", "Opcode", "Instruction",
    "BasicBlock", "FunctionIR", "ProgramIR",
    "IRPrinter", "IRDotGenerator", "IRGenerator"
]