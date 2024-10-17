# Hazardous
**Hazardous** is a compiled programming language.\
It runs by translating the source code to fasm (flat assembler) instructions, which is then compiled to an object file using fasm.
GCC is used to link the object files since I don't know how to make a proper linker (Tried really hard and got nowhere).

This is a project I totally forgot about. As of this writing it's been sitting on my computer untouched for 3 years.

_**Inefficient**_\
If you happen to look at the generated assembly, you'll see that it utilizes the stack a lot, which may be very inefficient. I wasn't able to figure out how to generate actual good assembly code so I just resorted to a stack model like some interpreted languages do.

Here's a simple Hello World program written using Hazardous.
```
%include "std.hz"

proc main(argc: i32, argv: u8**) -> i32 {
    printf("Hello World\n");
    return 0;
}
```

If you look at the following generated assembly you'll see what I'm talking about. You can imagine how inefficient this can be for large programs.
```nasm
format MS64 COFF
; bits 64
; default rel

section '.text' readable executable
    extrn malloc
    extrn free
    extrn printf
    extrn fclose
    extrn fopen
    extrn fread
    extrn fseek
    extrn ftell
    extrn rewind
    public main

main:
    push rbp
    mov rbp, rsp
    sub rsp, 16
    mov dword [rbp - 4], ecx
    mov qword [rbp - 16], rdx

    ; load string onto stack
    mov rax, __str_1
    push rax

    ; pop it into rcx (x64 calling convention)
    pop rcx

    ; call printf
    sub rsp, 32
    call printf
    add rsp, 32

    xor rax, rax
    push rax
    pop rax
    mov rsp, rbp
    pop rbp
    ret

section '.data' readable writeable
    __str_0: db 0x72,0x62,0x0
    __str_1: db 0x48,0x65,0x6c,0x6c,0x6f,0x20,0x57,0x6f,0x72,0x6c,0x64,0xa,0x0

; segment .bss
```

_**Self-hosted**_\
I planned for Hazardous to be self-hosted, and you can see in the repo that there was some progress made in that area before I eventually slowly stopped working on Hazardous.

_**Will I ever finish this?**_\
I would like to finish Hazardous some day as I did already put a lot of hours into it. When I decide to start working on it again, I might redo it all from scratch because I literally can't fully grasp the system again.