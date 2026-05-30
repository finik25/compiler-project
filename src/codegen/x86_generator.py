# src/codegen/x86_generator.py

from typing import List, Optional
from src.ir.ir_instructions import ProgramIR, FunctionIR, BasicBlock, Instruction, Operand, OperandType, Opcode
from src.codegen.abi import ARG_REGS, RET_REG, SYS_WRITE, SYS_EXIT, STDOUT
from src.codegen.stack_frame import StackFrameManager

class X86Generator:
    def __init__(self, enable_regalloc: bool = False):  # пока отключаем регистровую аллокацию
        self.enable_regalloc = enable_regalloc
        self.current_func: Optional[FunctionIR] = None
        self.stack_mgr: Optional[StackFrameManager] = None

    def generate(self, program: ProgramIR) -> str:
        lines = []
        lines.append("section .text")
        lines.append("global main")
        lines.append("")

        for func in program.functions:
            lines.extend(self._gen_function(func))
            lines.append("")

        lines.append("; ---- Runtime functions ----")
        lines.append(self._get_runtime_code())
        return "\n".join(lines)

    def _gen_function(self, func: FunctionIR) -> List[str]:
        self.current_func = func
        self.stack_mgr = StackFrameManager(func)
        self.stack_mgr.allocate()

        lines = []
        lines.append(f"{func.name}:")
        # Пролог
        lines.append("    push rbp")
        lines.append("    mov rbp, rsp")
        lines.append(f"    sub rsp, {self.stack_mgr.total_size}")

        # Сохраняем параметры из регистров в слоты соответствующих временных
        param_regs = ARG_REGS[:len(func.parameters)]
        for idx, param_name in enumerate(func.parameters):
            # Находим временную, связанную с параметром
            temp_op = func.var_map.get(param_name)
            if temp_op and temp_op.kind == OperandType.TEMP:
                temp_index = temp_op.value
                offset = self.stack_mgr.get_temp_offset(temp_index)
                reg = param_regs[idx] if idx < len(param_regs) else None
                if reg:
                    lines.append(f"    mov [rbp{offset:+d}], {reg}")

        # Генерация кода для блоков
        for block in func.blocks:
            lines.append(f".{block.label}:")
            for instr in block.instructions:
                lines.extend(self._gen_instruction(instr))

        # Добавляем эпилог, если в функции нет RETURN
        has_return = any(
            instr.opcode == Opcode.RETURN
            for blk in func.blocks
            for instr in blk.instructions
        )
        if not has_return:
            lines.append(".epilogue:")
            lines.append("    mov rsp, rbp")
            lines.append("    pop rbp")
            lines.append("    ret")
        return lines

    def _gen_instruction(self, instr: Instruction) -> List[str]:
        lines = []
        if instr.comment:
            lines.append(f"    ; {instr.comment}")

        if instr.opcode == Opcode.MOVE:
            lines.extend(self._gen_move(instr.dest, instr.src1))
        elif instr.opcode in (Opcode.ADD, Opcode.SUB, Opcode.MUL, Opcode.DIV,
                              Opcode.AND, Opcode.OR, Opcode.XOR):
            lines.extend(self._gen_binary(instr.opcode, instr.dest, instr.src1, instr.src2))
        elif instr.opcode in (Opcode.CMP_EQ, Opcode.CMP_NE, Opcode.CMP_LT, Opcode.CMP_LE,
                              Opcode.CMP_GT, Opcode.CMP_GE):
            lines.extend(self._gen_compare(instr.opcode, instr.dest, instr.src1, instr.src2))
        elif instr.opcode == Opcode.JUMP:
            lines.append(f"    jmp .{instr.label}")
        elif instr.opcode == Opcode.JUMP_IF:
            lines.extend(self._gen_jump_cond(instr.src1, instr.label, True))
        elif instr.opcode == Opcode.JUMP_IF_NOT:
            lines.extend(self._gen_jump_cond(instr.src1, instr.label, False))
        elif instr.opcode == Opcode.CALL:
            lines.extend(self._gen_call(instr))
        elif instr.opcode == Opcode.RETURN:
            if instr.src1:
                lines.extend(self._gen_load_into_reg(instr.src1, RET_REG))
            lines.append("    mov rsp, rbp")
            lines.append("    pop rbp")
            lines.append("    ret")
        return lines

    def _gen_move(self, dest: Operand, src: Operand) -> List[str]:
        lines = []
        if dest.kind == OperandType.TEMP:
            offset = self.stack_mgr.get_temp_offset(dest.value)
            # Загружаем src в rax и сохраняем в стек
            lines.extend(self._gen_load_into_reg(src, 'rax'))
            lines.append(f"    mov [rbp{offset:+d}], rax")
        return lines

    def _gen_binary(self, opcode: Opcode, dest: Operand, left: Operand, right: Operand) -> List[str]:
        lines = []
        # Результат будем накапливать в rax
        lines.extend(self._gen_load_into_reg(left, 'rax'))
        lines.extend(self._gen_load_into_reg(right, 'rbx'))

        if opcode == Opcode.DIV:
            lines.append("    xor rdx, rdx")
            lines.append("    div rbx")      # rax = rax / rbx (беззнаковое)
        elif opcode == Opcode.MUL:
            lines.append("    imul rax, rbx")
        else:
            asm_op = self._opcode_to_asm(opcode)
            lines.append(f"    {asm_op} rax, rbx")

        # Сохраняем результат в dest
        if dest.kind == OperandType.TEMP:
            offset = self.stack_mgr.get_temp_offset(dest.value)
            lines.append(f"    mov [rbp{offset:+d}], rax")
        return lines

    def _gen_compare(self, opcode: Opcode, dest: Operand, left: Operand, right: Operand) -> List[str]:
        lines = []
        lines.extend(self._gen_load_into_reg(left, 'rax'))
        lines.extend(self._gen_load_into_reg(right, 'rbx'))
        lines.append(f"    cmp rax, rbx")
        setcc_map = {
            Opcode.CMP_EQ: 'sete',
            Opcode.CMP_NE: 'setne',
            Opcode.CMP_LT: 'setl',
            Opcode.CMP_LE: 'setle',
            Opcode.CMP_GT: 'setg',
            Opcode.CMP_GE: 'setge',
        }
        setcc = setcc_map.get(opcode, 'sete')
        lines.append(f"    {setcc} al")
        lines.append("    movzx rax, al")
        if dest.kind == OperandType.TEMP:
            offset = self.stack_mgr.get_temp_offset(dest.value)
            lines.append(f"    mov [rbp{offset:+d}], rax")
        return lines

    def _gen_jump_cond(self, cond: Operand, label: str, jump_if_true: bool) -> List[str]:
        lines = []
        lines.extend(self._gen_load_into_reg(cond, 'rax'))
        lines.append("    cmp rax, 0")
        if jump_if_true:
            lines.append(f"    jne .{label}")
        else:
            lines.append(f"    je .{label}")
        return lines

    def _gen_call(self, instr: Instruction) -> List[str]:
        lines = []
        # Сохраняем caller-saved регистры (rax, rcx, rdx, rsi, rdi, r8-r11) – упрощённо: ничего не сохраняем,
        # так как все переменные у нас на стеке. Но нужно сохранять регистры, которые могут быть использованы
        # для аргументов (rdi, rsi, rdx, rcx, r8, r9) – они будут перезаписаны.
        # Поскольку мы не используем регистры для хранения переменных, достаточно просто установить аргументы.

        args = instr.args
        arg_regs = ARG_REGS[:len(args)]
        for i, arg in enumerate(args):
            if i < len(arg_regs):
                lines.extend(self._gen_load_into_reg(arg, arg_regs[i]))
        lines.append(f"    call {instr.label}")
        if instr.dest and instr.dest.kind == OperandType.TEMP:
            offset = self.stack_mgr.get_temp_offset(instr.dest.value)
            lines.append(f"    mov [rbp{offset:+d}], rax")
        return lines

    def _gen_load_into_reg(self, op: Operand, reg: str) -> List[str]:
        lines = []
        if op.kind == OperandType.CONST:
            lines.append(f"    mov {reg}, {op.value}")
        elif op.kind == OperandType.TEMP:
            offset = self.stack_mgr.get_temp_offset(op.value)
            lines.append(f"    mov {reg}, [rbp{offset:+d}]")
        elif op.kind == OperandType.SYMBOL:
            lines.append(f"    mov {reg}, [rel {op.value}]")
        elif op.kind == OperandType.LABEL:
            lines.append(f"    mov {reg}, .{op.value}")
        return lines

    def _opcode_to_asm(self, opcode: Opcode) -> str:
        mapping = {
            Opcode.ADD: 'add',
            Opcode.SUB: 'sub',
            Opcode.MUL: 'imul',
            Opcode.AND: 'and',
            Opcode.OR: 'or',
            Opcode.XOR: 'xor',
        }
        return mapping.get(opcode, '')

    def _get_runtime_code(self) -> str:
        return """
; print_int(rdi)
print_int:
    test rdi, rdi
    jns .positive
    push rdi
    mov rdi, '-'
    call print_char
    pop rdi
    neg rdi
.positive:
    jmp print_uint

print_uint:
    mov rax, rdi
    mov rcx, 10
    sub rsp, 32
    mov rsi, rsp
    add rsi, 31
    mov byte [rsi], 0xa
    dec rsi
.loop:
    xor rdx, rdx
    div rcx
    add dl, '0'
    mov [rsi], dl
    dec rsi
    test rax, rax
    jnz .loop
    inc rsi
    mov rax, 1
    mov rdi, 1
    mov rdx, rsp
    add rdx, 32
    sub rdx, rsi
    syscall
    add rsp, 32
    ret

print_char:
    push rax
    push rdi
    sub rsp, 8
    mov [rsp], dil
    mov rax, 1
    mov rdi, 1
    mov rsi, rsp
    mov rdx, 1
    syscall
    add rsp, 8
    pop rdi
    pop rax
    ret

exit:
    mov rax, 60
    syscall

_start:
    call main
    mov rdi, rax
    call exit
"""