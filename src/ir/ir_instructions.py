"""Data structures for three-address code IR with basic blocks and CFG."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Any, Dict


class OperandType(Enum):
    """Типы операндов IR."""
    TEMP = "temp"          # временная переменная t1, t2, ...
    CONST = "const"        # литерал (int, float, bool, string)
    LABEL = "label"        # метка блока L1, L2, ...
    SYMBOL = "symbol"      # глобальный символ (имя переменной или функции)


@dataclass
class Operand:
    """Операнд инструкции."""
    kind: OperandType
    value: Any                     # значение: int, str, или номер временной
    type_name: Optional[str] = None  # "int", "float", "bool", "void", "string"
    is_unsigned: bool = False  # новое поле

    def __str__(self) -> str:
        if self.kind == OperandType.TEMP:
            return f"t{self.value}"
        elif self.kind == OperandType.CONST:
            if isinstance(self.value, str):
                return f'"{self.value}"'
            return str(self.value)
        elif self.kind == OperandType.LABEL:
            return f"L{self.value}"
        else:  # SYMBOL
            return self.value

    @staticmethod
    def temp(index: int, type_name: Optional[str] = None, is_unsigned: bool = False) -> 'Operand':
        return Operand(OperandType.TEMP, index, type_name, is_unsigned)

    @staticmethod
    def const(value: Any, type_name: Optional[str] = None) -> 'Operand':
        return Operand(OperandType.CONST, value, type_name)

    @staticmethod
    def label(name: str) -> 'Operand':
        if isinstance(name, str) and name.startswith('L'):
            return Operand(OperandType.LABEL, name)
        else:
            return Operand(OperandType.LABEL, f"L{name}")

    @staticmethod
    def symbol(name: str, type_name: Optional[str] = None, is_unsigned: bool = False) -> 'Operand':
        return Operand(OperandType.SYMBOL, name, type_name, is_unsigned)


class Opcode(Enum):
    """Коды операций IR."""
    # Арифметика
    ADD = "ADD"
    SUB = "SUB"
    MUL = "MUL"
    DIV = "DIV"
    MOD = "MOD"
    NEG = "NEG"

    # Логические
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    XOR = "XOR"

    # Сравнения
    CMP_EQ = "CMP_EQ"
    CMP_NE = "CMP_NE"
    CMP_LT = "CMP_LT"
    CMP_LE = "CMP_LE"
    CMP_GT = "CMP_GT"
    CMP_GE = "CMP_GE"

    # Память
    LOAD = "LOAD"
    STORE = "STORE"
    ALLOCA = "ALLOCA"

    # Перемещение
    MOVE = "MOVE"

    # Управление потоком
    LABEL = "LABEL"
    JUMP = "JUMP"
    JUMP_IF = "JUMP_IF"
    JUMP_IF_NOT = "JUMP_IF_NOT"

    # Функции
    CALL = "CALL"
    RETURN = "RETURN"
    PARAM = "PARAM"
    PHI = "PHI"

    # Новые условные переходы (прямые)
    BR_EQ = "BR_EQ"
    BR_NE = "BR_NE"
    BR_LT = "BR_LT"
    BR_LE = "BR_LE"
    BR_GT = "BR_GT"
    BR_GE = "BR_GE"
    BR_ULT = "BR_ULT"  # беззнаковое <
    BR_ULE = "BR_ULE"  # беззнаковое <=
    BR_UGT = "BR_UGT"  # беззнаковое >
    BR_UGE = "BR_UGE"  # беззнаковое >=


@dataclass
class Instruction:
    """Одна инструкция трёхадресного кода."""
    opcode: Opcode
    dest: Optional[Operand] = None
    src1: Optional[Operand] = None
    src2: Optional[Operand] = None
    label: Optional[str] = None        # для LABEL, JUMP, JUMP_IF
    args: List[Operand] = field(default_factory=list)  # для CALL, PHI
    comment: Optional[str] = None
    is_unsigned: bool = False

    def __str__(self) -> str:
        parts = []
        if self.comment:
            parts.append(f"# {self.comment}")
        instr_str = self._format_instruction()
        parts.append(instr_str)
        return "\n".join(parts) if len(parts) > 1 else instr_str

    def _format_instruction(self) -> str:
        if self.opcode == Opcode.LABEL:
            return f"{self.label}:"
        elif self.opcode == Opcode.JUMP:
            return f"JUMP {self.label}"
        elif self.opcode == Opcode.JUMP_IF:
            return f"JUMP_IF {self.src1}, {self.label}"
        elif self.opcode == Opcode.JUMP_IF_NOT:
            return f"JUMP_IF_NOT {self.src1}, {self.label}"
        elif self.opcode == Opcode.CALL:
            args_str = ", ".join(str(a) for a in self.args)
            if self.dest:
                return f"{self.dest} = CALL {self.label}({args_str})"
            else:
                return f"CALL {self.label}({args_str})"
        elif self.opcode == Opcode.RETURN:
            if self.src1:
                return f"RETURN {self.src1}"
            else:
                return "RETURN"
        elif self.opcode == Opcode.PHI:
            phi_args = []
            for i in range(0, len(self.args), 2):
                val = self.args[i]
                lbl = self.args[i+1] if i+1 < len(self.args) else None
                phi_args.append(f"({val}, {lbl})")
            return f"{self.dest} = PHI " + ", ".join(phi_args)
        else:
            if self.dest and self.src2:
                return f"{self.dest} = {self.opcode.value} {self.src1}, {self.src2}"
            elif self.dest and self.src1:
                return f"{self.dest} = {self.opcode.value} {self.src1}"
            elif self.src2:
                return f"{self.opcode.value} {self.src1}, {self.src2}"
            elif self.src1:
                return f"{self.opcode.value} {self.src1}"
            else:
                return self.opcode.value

    # Фабричные методы
    @staticmethod
    def label_inst(label_name: str) -> 'Instruction':
        return Instruction(Opcode.LABEL, label=label_name)

    @staticmethod
    def jump(label_name: str) -> 'Instruction':
        return Instruction(Opcode.JUMP, label=label_name)

    @staticmethod
    def jump_if(cond: Operand, label_name: str) -> 'Instruction':
        return Instruction(Opcode.JUMP_IF, src1=cond, label=label_name)

    @staticmethod
    def jump_if_not(cond: Operand, label_name: str) -> 'Instruction':
        return Instruction(Opcode.JUMP_IF_NOT, src1=cond, label=label_name)

    @staticmethod
    def move(dest: Operand, src: Operand) -> 'Instruction':
        return Instruction(Opcode.MOVE, dest=dest, src1=src)

    @staticmethod
    def binary(op: Opcode, dest: Operand, left: Operand, right: Operand, is_unsigned: bool = False) -> 'Instruction':
        return Instruction(op, dest=dest, src1=left, src2=right, is_unsigned=is_unsigned)

    @staticmethod
    def unary(op: Opcode, dest: Operand, src: Operand) -> 'Instruction':
        return Instruction(op, dest=dest, src1=src)

    @staticmethod
    def load(dest: Operand, addr: Operand) -> 'Instruction':
        return Instruction(Opcode.LOAD, dest=dest, src1=addr)

    @staticmethod
    def store(addr: Operand, src: Operand) -> 'Instruction':
        return Instruction(Opcode.STORE, src1=addr, src2=src)

    @staticmethod
    def call(dest: Optional[Operand], func_name: str, args: List[Operand]) -> 'Instruction':
        return Instruction(Opcode.CALL, dest=dest, label=func_name, args=args)

    @staticmethod
    def ret(value: Optional[Operand] = None) -> 'Instruction':
        return Instruction(Opcode.RETURN, src1=value)


@dataclass
class BasicBlock:
    label: str
    instructions: List[Instruction] = field(default_factory=list)
    predecessors: List['BasicBlock'] = field(default_factory=list)
    successors: List['BasicBlock'] = field(default_factory=list)

    def add_instruction(self, instr: Instruction):
        self.instructions.append(instr)

    def __str__(self) -> str:
        lines = [f"{self.label}:"]
        for instr in self.instructions:
            lines.append(f"    {instr}")
        return "\n".join(lines)


@dataclass
class FunctionIR:
    name: str
    return_type: str
    parameters: List[str]
    blocks: List[BasicBlock]
    var_types: Dict[str, str]
    temp_counter: int = 0
    label_counter: int = 0               # новый счётчик для меток
    var_map: Dict[str, Operand] = field(default_factory=dict)

    def new_temp(self, type_name: str = "int", is_unsigned: bool = False) -> Operand:
        self.temp_counter += 1
        return Operand.temp(self.temp_counter, type_name, is_unsigned)

    def new_label(self, prefix: str = "L") -> str:
        """Создаёт новую уникальную метку в пределах функции."""
        self.label_counter += 1
        return f"{prefix}{self.label_counter}"

    def get_block(self, label: str) -> Optional[BasicBlock]:
        for blk in self.blocks:
            if blk.label == label:
                return blk
        return None

    def add_block(self, block: BasicBlock):
        self.blocks.append(block)


@dataclass
class ProgramIR:
    functions: List[FunctionIR]

    def get_function(self, name: str) -> Optional[FunctionIR]:
        for f in self.functions:
            if f.name == name:
                return f
        return None