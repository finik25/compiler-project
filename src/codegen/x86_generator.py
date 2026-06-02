# src/codegen/x86_generator.py
from typing import List, Optional
from src.ir.ir_instructions import ProgramIR, FunctionIR, Instruction, Operand, OperandType, Opcode
from src.codegen.abi import ARG_REGS, RET_REG
from src.codegen.stack_frame import StackFrameManager

class X86Generator:
    def __init__(self, enable_regalloc: bool = True):
        self.enable_regalloc = enable_regalloc
        self.current_func: Optional[FunctionIR] = None
        self.stack_mgr: Optional[StackFrameManager] = None
        self.callee_saved = ['rbx', 'r12', 'r13', 'r14', 'r15']

    def generate(self, program: ProgramIR, globals: dict = None) -> str:
        lines = []
        externs = set()
        for func in program.functions:
            if hasattr(func, 'is_external') and func.is_external:
                externs.add(func.name)

        # Строковые литералы (секция .rodata)
        if hasattr(self, 'string_literals') and self.string_literals:
            lines.append("section .rodata")
            for value, label in self.string_literals.items():
                escaped = value.replace('\\', '\\\\').replace('"', '\\"')
                lines.append(f'    {label}: db "{escaped}", 0')
            lines.append("")

        # Секции данных для глобальных переменных
        if globals:
            rodata_lines = []
            data_lines = []
            bss_lines = []
            for name, info in globals.items():
                typ, init_val, array_size = info
                if typ == "string":
                    escaped = init_val.replace('\\', '\\\\').replace('"', '\\"')
                    rodata_lines.append(f'    {name}: db "{escaped}", 0')
                elif array_size is not None:
                    elem_size = 4 if typ in ("int", "unsigned int", "bool") else 8
                    total_bytes = array_size * elem_size
                    if init_val is not None:
                        data_lines.append(f"    {name}: times {total_bytes} db 0")
                    else:
                        bss_lines.append(f"    {name}: resb {total_bytes}")
                else:
                    if init_val is not None:
                        data_lines.append(f"    {name}: dq {init_val}")
                    else:
                        bss_lines.append(f"    {name}: resq 1")
            if rodata_lines:
                lines.append("section .rodata")
                lines.extend(rodata_lines)
                lines.append("")
            if data_lines:
                lines.append("section .data")
                lines.extend(data_lines)
                lines.append("")
            if bss_lines:
                lines.append("section .bss")
                lines.extend(bss_lines)
                lines.append("")

        # Добавляем extern для вызванных стандартных функций
        for func in program.functions:
            for block in func.blocks:
                for instr in block.instructions:
                    if instr.opcode == Opcode.CALL and instr.label in ('printf', 'scanf', 'malloc', 'free'):
                        externs.add(instr.label)

        # Текстовая секция
        lines.append("section .text")
        for ext in externs:
            lines.append(f"extern {ext}")
        lines.append("global main")
        lines.append("")

        for func in program.functions:
            lines.extend(self._gen_function(func))
            lines.append("")

        lines.append("; ---- Runtime functions ----")
        lines.append(self._get_runtime_code())
        return "\n".join(lines)

    def _gen_function(self, func: FunctionIR) -> List[str]:
        if func.is_external:
            return []   # внешние функции не генерируем

        # Инициализация StackFrameManager для текущей функции
        self.stack_mgr = StackFrameManager(func)
        self.stack_mgr.allocate()
        self.current_func = func

        lines = []
        lines.append(f"{func.name}:")
        lines.append("    push rbp")
        lines.append("    mov rbp, rsp")

        # Сохраняем callee-saved регистры
        for reg in self.callee_saved:
            lines.append(f"    push {reg}")

        # Выравнивание стека до 16 байт (добавляем 8 байт)
        lines.append("    sub rsp, 8")
        # Выделяем память для локальных переменных
        lines.append(f"    sub rsp, {self.stack_mgr.total_size}")

        # Сохраняем параметры функции в стек
        param_regs = ARG_REGS[:len(func.parameters)]
        for idx, param_name in enumerate(func.parameters):
            temp_op = func.var_map.get(param_name)
            if temp_op and temp_op.kind == OperandType.TEMP:
                offset = self.stack_mgr.get_temp_offset(temp_op.value)
                reg = param_regs[idx] if idx < len(param_regs) else None
                if reg:
                    lines.append(f"    mov [rbp{offset:+d}], {reg}")

        # Генерация инструкций для всех блоков
        for block in func.blocks:
            lines.append(f".{block.label}:")
            for instr in block.instructions:
                lines.extend(self._gen_instruction(instr))

        # Если в функции нет ни одной инструкции RETURN, добавляем эпилог
        has_return = any(
            instr.opcode == Opcode.RETURN
            for blk in func.blocks
            for instr in blk.instructions
        )
        if not has_return:
            lines.append(f"    add rsp, {self.stack_mgr.total_size}")
            lines.append("    add rsp, 8")
            for reg in reversed(self.callee_saved):
                lines.append(f"    pop {reg}")
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
            lines.extend(self._gen_binary(instr.opcode, instr.dest, instr.src1, instr.src2, instr.is_unsigned))
        elif instr.opcode in (Opcode.CMP_EQ, Opcode.CMP_NE, Opcode.CMP_LT, Opcode.CMP_LE,
                              Opcode.CMP_GT, Opcode.CMP_GE):
            lines.extend(self._gen_compare(instr.opcode, instr.dest, instr.src1, instr.src2, instr.is_unsigned))
        elif instr.opcode == Opcode.JUMP:
            lines.append(f"    jmp .{instr.label}")
        elif instr.opcode == Opcode.JUMP_IF:
            lines.extend(self._gen_jump_cond(instr.src1, instr.label, True))
        elif instr.opcode == Opcode.JUMP_IF_NOT:
            lines.extend(self._gen_jump_cond(instr.src1, instr.label, False))
        elif instr.opcode in (Opcode.BR_EQ, Opcode.BR_NE, Opcode.BR_LT, Opcode.BR_LE,
                              Opcode.BR_GT, Opcode.BR_GE, Opcode.BR_ULT, Opcode.BR_ULE,
                              Opcode.BR_UGT, Opcode.BR_UGE):
            lines.extend(self._gen_cond_branch(instr))
        elif instr.opcode == Opcode.CALL:
            lines.extend(self._gen_call(instr))
        elif instr.opcode == Opcode.LOAD:
            # src1 – временная, содержащая адрес
            lines = []
            # Загружаем адрес в rax
            lines.extend(self._gen_load_into_reg(instr.src1, 'rax'))
            # Читаем значение по адресу
            lines.append(f"    mov rax, [rax]")
            # Сохраняем в dest
            dest_offset = self.stack_mgr.get_temp_offset(instr.dest.value)
            lines.append(f"    mov [rbp{dest_offset:+d}], rax")
            return lines
        elif instr.opcode == Opcode.STORE:
            # src1 – адрес (куда писать), src2 – значение
            lines = []
            lines.extend(self._gen_load_into_reg(instr.src1, 'rax'))
            lines.extend(self._gen_load_into_reg(instr.src2, 'rbx'))
            lines.append(f"    mov [rax], rbx")
            return lines
        elif instr.opcode == Opcode.ADDR:
            # dest = адрес src1 (переменной)
            lines = []
            # Загружаем адрес в rax
            if instr.src1.kind == OperandType.TEMP:
                # Локальная переменная – берём её смещение из stack_mgr
                offset = self.stack_mgr.get_temp_offset(instr.src1.value)
                lines.append(f"    lea rax, [rbp{offset:+d}]")
            elif instr.src1.kind == OperandType.SYMBOL:
                # Глобальная переменная – адрес через mov
                lines.append(f"    mov rax, {instr.src1.value}")
            else:
                raise NotImplementedError(f"ADDR source type {instr.src1.kind}")
            # Сохраняем адрес в dest (временную)
            dest_offset = self.stack_mgr.get_temp_offset(instr.dest.value)
            lines.append(f"    mov [rbp{dest_offset:+d}], rax")
            return lines
        elif instr.opcode == Opcode.RETURN:
            if instr.src1:
                lines.extend(self._gen_load_into_reg(instr.src1, 'rax'))
            # Эпилог: освобождаем локальные переменные, убираем выравнивание, восстанавливаем регистры
            lines.append(f"    add rsp, {self.stack_mgr.total_size}")
            lines.append("    add rsp, 8")
            for reg in reversed(self.callee_saved):
                lines.append(f"    pop {reg}")
            lines.append("    pop rbp")
            lines.append("    ret")
        return lines

    def _gen_move(self, dest: Operand, src: Operand) -> List[str]:
        lines = []
        if dest.kind == OperandType.TEMP:
            offset = self.stack_mgr.get_temp_offset(dest.value)
            lines.extend(self._gen_load_into_reg(src, 'rax'))
            lines.append(f"    mov [rbp{offset:+d}], rax")
        elif dest.kind == OperandType.SYMBOL:
            lines.extend(self._gen_load_into_reg(src, 'rax'))
            lines.append(f"    mov [rel {dest.value}], rax")
        return lines

    def _gen_binary(self, opcode: Opcode, dest: Operand, left: Operand, right: Operand, is_unsigned: bool = False) -> List[str]:
        lines = []
        lines.extend(self._gen_load_into_reg(left, 'rax'))
        lines.extend(self._gen_load_into_reg(right, 'rbx'))
        if opcode == Opcode.DIV:
            lines.append("    xor rdx, rdx")
            if is_unsigned:
                lines.append("    div rbx")
            else:
                lines.append("    idiv rbx")
        elif opcode == Opcode.MUL:
            if is_unsigned:
                lines.append("    mul rbx")
            else:
                lines.append("    imul rax, rbx")
        else:
            asm_op = self._opcode_to_asm(opcode)
            lines.append(f"    {asm_op} rax, rbx")
        if dest.kind == OperandType.TEMP:
            offset = self.stack_mgr.get_temp_offset(dest.value)
            lines.append(f"    mov [rbp{offset:+d}], rax")
        return lines

    def _gen_compare(self, opcode: Opcode, dest: Operand, left: Operand, right: Operand, is_unsigned: bool = False) -> List[str]:
        lines = []
        lines.extend(self._gen_load_into_reg(left, 'rax'))
        lines.extend(self._gen_load_into_reg(right, 'rbx'))
        lines.append(f"    cmp rax, rbx")
        if is_unsigned:
            setcc_map = {
                Opcode.CMP_EQ: 'sete',
                Opcode.CMP_NE: 'setne',
                Opcode.CMP_LT: 'setb',
                Opcode.CMP_LE: 'setbe',
                Opcode.CMP_GT: 'seta',
                Opcode.CMP_GE: 'setae',
            }
        else:
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

    def _gen_cond_branch(self, instr: Instruction) -> List[str]:
        """Генерирует код для прямого условного перехода BR_*."""
        lines = []
        # Загружаем операнды
        lines.extend(self._gen_load_into_reg(instr.src1, 'rax'))
        lines.extend(self._gen_load_into_reg(instr.src2, 'rbx'))
        lines.append("    cmp rax, rbx")
        # Выбираем ассемблерный мнемоник
        asm_jcc = {
            Opcode.BR_EQ: 'je',
            Opcode.BR_NE: 'jne',
            Opcode.BR_LT: 'jl',
            Opcode.BR_LE: 'jle',
            Opcode.BR_GT: 'jg',
            Opcode.BR_GE: 'jge',
            Opcode.BR_ULT: 'jb',
            Opcode.BR_ULE: 'jbe',
            Opcode.BR_UGT: 'ja',
            Opcode.BR_UGE: 'jae',
        }[instr.opcode]
        lines.append(f"    {asm_jcc} .{instr.label}")
        # Безусловный переход на false_label будет следующей инструкцией (JUMP)
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
        args = instr.args
        num_int_args = len(args)
        regs = ARG_REGS  # 6 регистров
        # Определяем, сколько аргументов пойдёт на стек
        stack_args_count = max(0, num_int_args - len(regs))
        # Выделяем место на стеке
        stack_bytes = stack_args_count * 8
        if stack_bytes:
            lines.append(f"    sub rsp, {stack_bytes}")
        # Загружаем регистровые аргументы
        for i, arg in enumerate(args):
            if i < len(regs):
                lines.extend(self._gen_load_into_reg(arg, regs[i]))
        # Записываем стековые аргументы (с конца списка, чтобы правый был ближе к вершине)
        for i in range(stack_args_count):
            arg_idx = num_int_args - stack_args_count + i
            arg = args[arg_idx]
            offset = i * 8
            lines.extend(self._gen_load_into_reg(arg, 'rax'))
            lines.append(f"    mov [rsp+{offset}], rax")
        # Вариадическая функция: al = 0
        if instr.label in ('printf', 'scanf'):
            lines.append("    xor eax, eax")
        lines.append(f"    call {instr.label}")
        if stack_bytes:
            lines.append(f"    add rsp, {stack_bytes}")
        if instr.dest and instr.dest.kind == OperandType.TEMP:
            offset = self.stack_mgr.get_temp_offset(instr.dest.value)
            lines.append(f"    mov [rbp{offset:+d}], rax")
        return lines

    def _gen_load_into_reg(self, op: Operand, reg: str) -> List[str]:
        if not isinstance(op, Operand):
            raise TypeError(f"Expected Operand, got {type(op)}: {op}")
        lines = []
        if op.kind == OperandType.CONST:
            lines.append(f"    mov {reg}, {op.value}")
        elif op.kind == OperandType.TEMP:
            if op.is_address:
                offset = self.stack_mgr.get_temp_offset(op.value)
                lines.append(f"    lea {reg}, [rbp{offset:+d}]")
            else:
                offset = self.stack_mgr.get_temp_offset(op.value)
                lines.append(f"    mov {reg}, [rbp{offset:+d}]")
        elif op.kind == OperandType.SYMBOL and op.type_name == "string":
            lines.append(f"    lea {reg}, [rel {op.value}]")
        elif op.kind == OperandType.SYMBOL:
            if op.is_address:
                lines.append(f"    mov {reg}, {op.value}")
            else:
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