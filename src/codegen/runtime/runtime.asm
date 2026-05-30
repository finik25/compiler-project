; runtime.asm
section .text

global print_int
global print_char
global exit
global _start

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
    mov rbx, rsp
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