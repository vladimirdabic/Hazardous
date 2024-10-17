from dataclasses import field
from . import nodes
from .scanner import TokenType, TokenLocation
from .nodes import Cast, TypeEnum
from .localdict import LocalDict
import pprint



ASM_TEMPLATE = """
format MS64 COFF
; bits 64
; default rel

section '.text' readable executable
{externs}

{functions}

section '.data' readable writeable
{data}

; segment .bss
{bss}
"""

ARGUMENT_REGISTERS = ('rcx', 'rdx', 'r8', 'r9')

TYPE_SIZES = {
    TypeEnum.U8: 1,
    TypeEnum.U16: 2,
    TypeEnum.U32: 4,
    TypeEnum.U64: 8,
    TypeEnum.I8: 1,
    TypeEnum.I16: 2,
    TypeEnum.I32: 4,
    TypeEnum.I64: 8,
    TypeEnum.PTR: 8,
    TypeEnum.PROCPTR: 8,
    TypeEnum.STRUCT: 8,
    TypeEnum.SUB_STRUCT: 8,
    TypeEnum.CLASS: 8
}

ASM_TYPE_NAMES = {
    TypeEnum.U8: "byte",
    TypeEnum.U16: "word",
    TypeEnum.U32: "dword",
    TypeEnum.U64: "qword",
    TypeEnum.I8: "byte",
    TypeEnum.I16: "word",
    TypeEnum.I32: "dword",
    TypeEnum.I64: "qword",
    TypeEnum.PTR: "qword",
    TypeEnum.PROCPTR: "qword",
    TypeEnum.CLASS: "qword",
    TypeEnum.STRUCT: "qword",
    TypeEnum.SUB_STRUCT: "qword"
}

TYPE_NAMES = {
    TypeEnum.U8: "u8",
    TypeEnum.U16: "u16",
    TypeEnum.U32: "u32",
    TypeEnum.U64: "u64",
    TypeEnum.I8: "i8",
    TypeEnum.I16: "i16",
    TypeEnum.I32: "i32",
    TypeEnum.I64: "i64",
    TypeEnum.PTR: "ptr",
    TypeEnum.PROCPTR: "procptr",
    TypeEnum.CLASS: "class",
    TypeEnum.STRUCT: "struct",
    TypeEnum.SUB_STRUCT: "struct"
}

ASM_TYPE_LETTERS = {
    TypeEnum.U8: 'b',
    TypeEnum.U16: 'w',
    TypeEnum.U32: 'd',
    TypeEnum.U64: 'q',
    TypeEnum.I8: 'b',
    TypeEnum.I16: 'w',
    TypeEnum.I32: 'd',
    TypeEnum.I64: 'q',
    TypeEnum.PTR: 'q',
    TypeEnum.PROCPTR: 'q',
    TypeEnum.CLASS: 'q',
    TypeEnum.STRUCT: 'q',
    TypeEnum.SUB_STRUCT: 'q'
}

REGISTER_VARIATIONS = {
    "rax": {
        1: "al",
        2: "ax",
        4: "eax",
        8: "rax"
    },
    "rbx": {
        1: "bl",
        2: "bx",
        4: "ebx",
        8: "rbx"
    },
    "rcx": {
        1: "cl",
        2: "cx",
        4: "ecx",
        8: "rcx"
    },
    "rdx": {
        1: "dl",
        2: "dx",
        4: "edx",
        8: "rdx"
    },
        "rdi": {
        1: "dil",
        2: "di",
        4: "edi",
        8: "rdi"
    },
    "rsi": {
        1: "sil",
        2: "si",
        4: "esi",
        8: "rsi"
    }
}


for i in range(8, 16):
    REGISTER_VARIATIONS[f"r{i}"] = {
        1: f"r{i}b",
        2: f"r{i}w",
        4: f"r{i}d",
        8: f"r{i}"
}

BINARY_OPERATIONS = {
    TokenType.PLUS: [
        'pop rax',
        'pop rbx',
        'add rax, rbx',
        'push rax'
    ],
    TokenType.MINUS: [
        'pop rax',
        'pop rbx',
        'sub rax, rbx',
        'push rax'
    ],
    TokenType.STAR: [
        'pop rax',
        'pop rbx',
        'mul rbx',
        'push rax'
    ],
    TokenType.SLASH: [
        'xor rdx, rdx',
        'pop rax',
        'pop rbx',
        'div rbx',
        'push rax'
    ],
    TokenType.DEQUALS: [
        'pop rax',
        'pop rbx',
        'cmp rax, rbx',
        'sete al',
        'movzx rax, al',
        'push rax'
    ],
    TokenType.NEQUALS: [
        'pop rax',
        'pop rbx',
        'cmp rax, rbx',
        'setne al',
        'movzx rax, al',
        'push rax'
    ],
    TokenType.GREATER: [
        'pop rax',
        'pop rbx',
        'cmp rax, rbx',
        'setg al',
        'movzx rax, al',
        'push rax'
    ],
    TokenType.LOWER: [
        'pop rax',
        'pop rbx',
        'sub rbx, 1',
        'cmp rax, rbx',
        'setle al',
        'movzx rax, al',
        'push rax'
    ],
    TokenType.LEQUALS: [
        'pop rax',
        'pop rbx',
        'cmp rax, rbx',
        'setle al',
        'movzx rax, al',
        'push rax'
    ],
    TokenType.GEQUALS: [
        'pop rax',
        'pop rbx',
        'sub rbx, 1',
        'cmp rax, rbx',
        'setg al',
        'movzx rax, al',
        'push rax'
    ],
    TokenType.PRECENT: [
        'xor rdx, rdx',
        'pop rax',
        'pop rbx',
        'div rbx',
        'push rdx'
    ],
    TokenType.ARROW_UP: [
        'pop rax',
        'pop rbx',
        'xor rax, rbx',
        'push rax'
    ],
    TokenType.PIPE: [
        'pop rax',
        'pop rbx',
        'or rax, rbx',
        'push rax'
    ],
    TokenType.AMPERSAND: [
        'pop rax',
        'pop rbx',
        'and rax, rbx',
        'push rax'
    ]
}


class Generator:
    def generate(self, program_tree):
        self.current_id = 0
        self.current_label = 0
        self.bss = {}
        self.data = {}
        self.externs = []
        self.functions = {}
        self.current_function = None
        self.current_body = None
        self.current_locals = LocalDict()
        self.globals = {}
        self.struct_data = {}
        self.class_data = {}
        self.enum_data = {}
        self.break_stack = []

        self.functions['malloc'] = {
            "return_type": nodes.Type(id=TypeEnum.PTR),
            "arguments": [(nodes.Type(id=TypeEnum.U64), 'size')],
            "extern": True,
            "varargs": False,
            "stdcall": False,
            "called": True,
            "is_local": True
        }

        self.functions['free'] = {
            "return_type": nodes.Type(id=TypeEnum.NONE),
            "arguments": [(nodes.Type(id=TypeEnum.PTR), 'ptr')],
            "extern": True,
            "varargs": False,
            "stdcall": False,
            "called": True,
            "is_local": True
        }

        self.externs.append('extrn malloc')
        self.externs.append('extrn free')

        # generate class and struct data
        for node in program_tree:
            if isinstance(node, (nodes.ProgramClass, nodes.ProgramStruct)):
               self._generate_node(node) 

            elif isinstance(node, nodes.ProgramProcedure):
                self.functions[node.name] = {
                    "return_type": node.return_type,
                    "arguments": node.args,
                    "extern": False,
                    "varargs": node.varargs,
                    "stdcall": node.stdcall,
                    "called": node.always,
                    "body": None,
                    "is_local": node.is_local
                }

        for node in program_tree:
            if not isinstance(node, (nodes.ProgramClass, nodes.ProgramStruct)):
                self._generate_node(node)


        funcs = ""

        for func_name, func_data in self.functions.items():
            if not func_data['extern'] and func_data['body']:
                if func_data['called']:
                    body = '\n'.join(f'    {line}' for line in func_data['body'])
                    funcs += f"{func_name}:\n{body}\n\n"
                elif not func_data['is_local']:
                    self.externs.remove(f"public {func_name}")

            elif func_data['extern'] and not func_data['called']:
                self.externs.remove(f"extrn {func_name}")

        data_txt = '\n'.join(f"    {data_name}: d{ASM_TYPE_LETTERS[data_values[0]]} {data_values[1]}" for data_name, data_values in self.data.items())
        bss_txt =  '\n'.join(f"    {bss_name}: r{ASM_TYPE_LETTERS[bss_values[0]]} {bss_values[1]}" for bss_name, bss_values in self.bss.items())
        extern_txt =  '\n'.join(f"    {extern_name}" for extern_name in self.externs)

        return ASM_TEMPLATE.format(bss=bss_txt, data=data_txt, functions=funcs, externs=extern_txt)

    def _generate_node(self, node):
        name = type(node).__name__
        method = getattr(self, f"_generate_{name}", None)

        if not method:
            raise NotImplementedError(f"Generator for node type '{name}' hasn't been implemented.")

        method(node)


    def _generate_ProgramVariable(self, node: nodes.ProgramVariable):
        self.globals[node.name] = {
            "type": node.type
        }

        self.bss[node.name] = (node.type.id, 1)

        if not node.is_local:
            # global {node.name}
            if f'public {node.name}' not in self.externs:
                self.externs.append(f'public {node.name}')


    def _generate_ProgramProcedure(self, node: nodes.ProgramProcedure):
        func_data = self.functions.get(node.name, None)

        if not func_data:
            self.functions[node.name] = {
                "return_type": node.return_type,
                "arguments": node.args,
                "extern": False,
                "varargs": node.varargs,
                "stdcall": node.stdcall,
                "called": node.always,
                "body": None,
                "is_local": node.is_local,
            }
            
        if node.forward_declared:
            return

        func_data['body'] = [
            'push rbp',
            'mov rbp, rsp',
            'sub rsp, SIZE'
        ]

        if node.name == "main":
            func_data['called'] = True

        self.current_function = node.name
        self.current_body = func_data['body']
        self.current_locals = LocalDict()
        self.local_offset = 0
        self.max_align = 1
        self.current_label = 0

        if not node.is_local:
            # global {node.name}
            if f'public {node.name}' not in self.externs:
                self.externs.append(f'public {node.name}')

        arg_registers = len(ARGUMENT_REGISTERS)

        for i, (arg_type, arg_name) in enumerate(node.args):
            arg_type_size, arg_type_name = TYPE_SIZES[arg_type.id], ASM_TYPE_NAMES[arg_type.id]
            self._generate_LocalVariable(nodes.LocalVariable(name=arg_name, location=node.location, type=arg_type, value=None))
            # move parameter into the local variable
            if i < arg_registers:
                self.current_body.append(f'mov {arg_type_name.lower()} [rbp - {self.local_offset}], {REGISTER_VARIATIONS[ARGUMENT_REGISTERS[i]][arg_type_size]}')
            # read parameter from the stack
            else:
                # rbp + 48 = first parameter
                self.current_body.append(f'mov {REGISTER_VARIATIONS["rax"][arg_type_size]}, {arg_type_name.lower()} [rbp + {48 + ((i - 4) * 8)}]')
                self.current_body.append(f'mov {arg_type_name.lower()} [rbp - {self.local_offset}], {REGISTER_VARIATIONS["rax"][arg_type_size]}')
                

        for statement in node.body:
            self._generate_node(statement)

        rem = self.local_offset % self.max_align
        if rem != 0:
            self.local_offset += self.max_align - rem

        if self.current_locals:
            aligned_locals, remainder = (self.local_offset // 16), (self.local_offset % 16 > 0)
            self.current_body[2] = f'sub rsp, {aligned_locals * 16 + (16 * remainder)}'
        else:
            self.current_body.pop(2)


        if node.return_type.id == TypeEnum.NONE and self.current_body[-1] != 'ret':
            self.current_body.append('mov rsp, rbp')
            self.current_body.append('pop rbp')
            self.current_body.append('ret')

        else:
            if self.current_body[-1] != 'ret':
                raise GeneratorError(f"Missing return statement in procedure '{node.name}'", node.location)

    def _generate_LocalVariable(self, node: nodes.LocalVariable):
        if node.type:
            type_size, type_name = TYPE_SIZES[node.type.id], ASM_TYPE_NAMES[node.type.id]
            padding = 0
            
            if node.type.id == TypeEnum.SUB_STRUCT:
                struct_data = self.calculate_struct(node.type.data['fields'])
                array_size = struct_data['size']
                node.type.data = struct_data

                self.local_offset += array_size + (array_size % 8)
                array_offset = self.local_offset
            
                if 8 > self.max_align:
                    self.max_align = 8

                #padding = 0
                remainder = self.local_offset % 8

                if self.local_offset > 0 and remainder != 0:
                    padding = 8 - remainder

                padded_size = 8 + padding
                self.local_offset += padded_size

                self.current_locals[node.name] = {
                    "size": 8,
                    "type": node.type,
                    "offset": self.local_offset
                }

                if not node.value:
                    ptr_offset = self.local_offset
                    self.current_body.append(f'lea rax, [rbp - {array_offset}]')
                    self.current_body.append(f'mov qword [rbp - {ptr_offset}], rax')

            else:
                if type_size > self.max_align:
                    self.max_align = type_size

                #padding = 0
                remainder = self.local_offset % type_size

                if self.local_offset > 0 and remainder != 0:
                    padding = type_size - remainder

                padded_size = type_size + padding
                self.local_offset += padded_size

                self.current_locals[node.name] = {
                    "size": type_size,
                    "type": node.type,
                    "offset": self.local_offset
                }
        else:
            if not node.value:
                assert False, "Unreachable, auto type value is none"

            resolved_type = self.resolve_type(node.value)
            type_size = TYPE_SIZES[resolved_type.id]
            type_name = ASM_TYPE_NAMES[resolved_type.id]

            if type_size > self.max_align:
                self.max_align = type_size

            padding = 0
            remainder = self.local_offset % type_size

            if self.local_offset > 0 and remainder != 0:
                padding = type_size - remainder

            padded_size = type_size + padding
            self.local_offset += padded_size
            var_offset = self.local_offset

            self.current_locals[node.name] = {
                "size": type_size,
                "type": resolved_type,
                "offset": var_offset
            }

            self._generate_node(node.value)
            self.current_body.append('pop rax')
            self.current_body.append(f'mov {type_name.lower()} [rbp - {var_offset}], {REGISTER_VARIATIONS["rax"][type_size]}')
            return


        # generate value set
        if not node.value:
            return

        resolved_type = self.resolve_type(node.value)

        assert resolved_type is not None, "FAILED AT LOC %s:%d:%d" % node.location

        self.validate_type(node.type, resolved_type, node.location, "Tried assinging non matching types for variable '{}', expected '{}', but got '{}'", node.name, self.get_type_name(node.type), self.get_type_name(resolved_type))

        var_offset = self.local_offset
        self._generate_node(node.value)
        self.current_body.append('pop rax')
        self.current_body.append(f'mov {type_name.lower()} [rbp - {var_offset}], {REGISTER_VARIATIONS["rax"][type_size]}')

    def _generate_LocalArray(self, node: nodes.LocalArray):
        type_size = TYPE_SIZES[node.type.id]
        array_size = node.size * type_size

        self.local_offset += array_size + (array_size % 8)
        array_offset = self.local_offset
    
        if 8 > self.max_align:
            self.max_align = 8

        padding = 0
        remainder = self.local_offset % 8

        if self.local_offset > 0 and remainder != 0:
            padding = 8 - remainder

        padded_size = 8 + padding
        self.local_offset += padded_size

        self.current_locals[node.name] = {
            "size": 8,
            "type": nodes.Type(id=TypeEnum.PTR, is_base_type=False,base_type=node.type),
            "offset": self.local_offset
        }

        ptr_offset = self.local_offset

        self.current_body.append(f'lea rax, [rbp - {array_offset}]')
        self.current_body.append(f'mov qword [rbp - {ptr_offset}], rax')

    def _generate_LocalStruct(self, node: nodes.LocalStruct):
        name = node.type.data['struct_name'] if node.type.id == TypeEnum.STRUCT else node.type.data['class_name']

        struct_data = self.struct_data[name]
        array_size = struct_data['size']

        self.local_offset += array_size + (array_size % 8)
        array_offset = self.local_offset
    
        if 8 > self.max_align:
            self.max_align = 8

        padding = 0
        remainder = self.local_offset % 8

        if self.local_offset > 0 and remainder != 0:
            padding = 8 - remainder

        padded_size = 8 + padding
        self.local_offset += padded_size

        self.current_locals[node.name] = {
            "size": 8,
            "type": node.type,
            "offset": self.local_offset
        }

        ptr_offset = self.local_offset

        self.current_body.append(f'lea rax, [rbp - {array_offset}]')
        self.current_body.append(f'mov qword [rbp - {ptr_offset}], rax')

    def _generate_AssignVariable(self, node: nodes.AssignVariable):
        resolved_type = self.resolve_type(node.value)

        if node.name in self.current_locals:
            var_type = self.current_locals[node.name]['type']
            offset = self.current_locals[node.name]['offset']
            type_size, type_name = TYPE_SIZES[var_type.id], ASM_TYPE_NAMES[var_type.id]

            
            #if var_type.type == TypeEnum.PTR and resolved_type.type != TypeEnum.PTR or resolved_type.type == TypeEnum.PTR and var_type.type != TypeEnum.PTR:
            #    raise GeneratorError(f"Tried assinging non matching types for variable '{node.name}', expected '{self.get_type_name(var_type)}', but got '{self.get_type_name(resolved_type)}'", node.location)

            self.validate_type(var_type, resolved_type, node.location, "Tried assinging non matching types for variable '{}', expected '{}', but got '{}'", node.name, self.get_type_name(var_type), self.get_type_name(resolved_type))

            self._generate_node(node.value)
            self.current_body.append('pop rax')
            self.current_body.append(f'mov {type_name.lower()} [rbp - {offset}], {REGISTER_VARIATIONS["rax"][type_size]}')
            self.current_body.append('push rax')

        elif node.name in self.globals:
            var_type = self.globals[node.name]['type']
            type_size, type_name = TYPE_SIZES[var_type.id], ASM_TYPE_NAMES[var_type.id]

            #if var_type.type == TypeEnum.PTR and resolved_type.type != TypeEnum.PTR or resolved_type.type == TypeEnum.PTR and var_type.type != TypeEnum.PTR:
            #    raise GeneratorError(f"Tried assinging non matching types for variable '{node.name}', expected '{self.get_type_name(var_type)}', but got '{self.get_type_name(resolved_type)}'", node.location)

            self.validate_type(var_type, resolved_type, node.location, "Tried assinging non matching types for variable '{}', expected '{}', but got '{}'", node.name, self.get_type_name(var_type), self.get_type_name(resolved_type))

            self._generate_node(node.value)
            self.current_body.append('pop rax')
            self.current_body.append(f'mov {type_name.lower()} [{node.name}], {REGISTER_VARIATIONS["rax"][type_size]}')
            self.current_body.append('push rax')

        else:
            raise GeneratorError(f"Attempted assinging to an undefined variable '{node.name}'", node.location)

    def _generate_Number(self, node: nodes.Number):
        if node.value == 0:
            self.current_body.append("xor rax, rax")
        else:
            self.current_body.append(f'mov rax, {node.value}')
        
        self.current_body.append('push rax')

    def _generate_String(self, node: nodes.String):
        string_parsed: str = node.value[1:-1]
        string_parsed = string_parsed.replace('\\n', '\n')
        string_parsed = string_parsed.replace('\\r', '\r')
        string_parsed = string_parsed.replace('\\"', '\"')
        string_parsed = string_parsed.replace('\\0', '\0')
        string_parsed = string_parsed.replace('\\\\', '\\')
        string_parsed = string_parsed + '\0'
        string_hex = ','.join(map(hex, list(string_parsed.encode('utf-8'))))
        self.data[f"__str_{self.current_id}"] = (TypeEnum.U8, string_hex)
        if self.current_body is not None:
            self.current_body.append(f'mov rax, __str_{self.current_id}')
            self.current_body.append('push rax')
        self.current_id += 1

    def _generate_Variable(self, node: nodes.Variable):
        if node.name in self.current_locals:
            type_id = self.current_locals[node.name]['type'].id

            type_name = ASM_TYPE_NAMES[type_id]
            type_size = TYPE_SIZES[type_id]
            offset = self.current_locals[node.name]['offset']

            if type_size != 8:
                if type_id in [TypeEnum.I8, TypeEnum.I16, TypeEnum.I32]:
                    # self.current_body.append(f'movsx rax, {type_name.lower()} [rbp - {offset}]')
                    self.current_body.append(f'mov eax, dword [rbp - {offset}]')
                else:
                    #self.current_body.append(f'movzx rax, {REGISTER_VARIATIONS["rax"][type_size]}')
                    if type_size != 4:
                        self.current_body.append(f'mov rax, [rbp - {offset}]')
                        self.current_body.append(f'movzx rax, {REGISTER_VARIATIONS["rax"][type_size]}')
                    else:
                        self.current_body.append(f"mov eax, dword [rbp - {offset}]")
            else:
                self.current_body.append(f'mov rax, {type_name.lower()} [rbp - {offset}]')
            
        elif node.name in self.globals:
            type_id = self.globals[node.name]['type'].id
            type_name = ASM_TYPE_NAMES[type_id]
            type_size = TYPE_SIZES[type_id]

            if type_size != 8:
                if type_id in [TypeEnum.I8, TypeEnum.I16, TypeEnum.I32]:
                    # self.current_body.append(f'movsx rax, {type_name.lower()} [{node.name}]')
                    self.current_body.append(f'mov eax, {type_name.lower()} [{node.name}]')
                else:
                    #self.current_body.append(f'movzx rax, {REGISTER_VARIATIONS["rax"][type_size]}')
                    if type_size != 4:
                        self.current_body.append(f'mov rax, [{node.name}]')
                        self.current_body.append(f'movzx rax, {REGISTER_VARIATIONS["rax"][type_size]}')
                    else:
                        self.current_body.append(f"mov eax, dword [{node.name}]")
            else:
                self.current_body.append(f'mov rax, [{node.name}]')
        else:
            raise GeneratorError(f"Unknown variable '{node.name}'", node.location)

        self.current_body.append('push rax')

    def _generate_BinaryOperation(self, node: nodes.BinaryOperation):
        if node.operation == TokenType.AND:
            self._generate_node(node.left)

            not_true_jmp = self.current_label
            self.current_label += 1
           
            self.current_body.extend([
                'pop rax',
                'cmp rax, 0',
                f'je .L{not_true_jmp}'
            ])

            self._generate_node(node.right)

            self.current_body.extend([
                'pop rax',
                'cmp rax, 0',
                'setne al',
                'movzx rax, al',
                'push rax',
                f'jmp .L{self.current_label}',
                f'.L{not_true_jmp}:',
                'mov rax, 0',
                'push rax',
                f'.L{self.current_label}:'
            ])

            self.current_label += 1
            return

        elif node.operation == TokenType.OR:
            self._generate_node(node.left)

            not_true_jmp = self.current_label
            self.current_label += 1
           
            self.current_body.extend([
                'pop rax',
                'cmp rax, 0',
                f'jne .L{not_true_jmp}'
            ])

            self._generate_node(node.right)

            self.current_body.extend([
                'pop rax',
                'cmp rax, 0',
                'setne al',
                'movzx rax, al',
                'push rax',
                f'jmp .L{self.current_label}',
                f'.L{not_true_jmp}:',
                'mov rax, 1',
                'push rax',
                f'.L{self.current_label}:'
            ])

            self.current_label += 1
            return

        self._generate_node(node.right)
        self._generate_node(node.left)
        self.current_body.extend(BINARY_OPERATIONS[node.operation])

    def _generate_Cast(self, node: nodes.Cast):
        self._generate_node(node.value)

    def _generate_ExpressionStatement(self, node: nodes.ExpressionStatement):
        self._generate_node(node.value)
        self.current_body.pop()
    
    def _generate_CallFunction(self, node: nodes.CallFunction):
        func_name = node.name

        if func_name not in self.functions:
            raise GeneratorError(f"Tried calling an undefined procedure '{func_name}'", node.location)

        callee_args = self.functions[func_name]['arguments']
        self.functions[func_name]['called'] = True
        caller_args_len = len(node.args)
        callee_args_len = len(callee_args)

        if caller_args_len < callee_args_len:
            raise GeneratorError(f"Too few arguments passed to procedure '{func_name}'", node.location)

        if caller_args_len > callee_args_len and not self.functions[func_name]['varargs']:
            raise GeneratorError(f"Too many arguments passed to procedure '{func_name}'", node.location)

        # Check types passed to function
        for i, (caller_value, (callee_type, callee_name)) in enumerate(zip(node.args, callee_args)):
            resolved_type = self.resolve_type(caller_value)
            assert resolved_type is not None, f"fail {node.name} {i}"
            self.validate_argument(callee_type, resolved_type, node.name, i+1, node.location)

        for i, arg in reversed(list(enumerate(node.args))):
            self._generate_node(arg)

        for i in range(min(caller_args_len, len(ARGUMENT_REGISTERS))):
            self.current_body.append(f'pop {ARGUMENT_REGISTERS[i]}')

        self.current_body.append(f'sub rsp, 32')
        self.current_body.append(f'call {func_name}')
        if not self.functions[func_name]['stdcall']:
            self.current_body.append(f'add rsp, {32 + max(caller_args_len - 4, 0) * 8}')
        self.current_body.append('push rax')

    def _generate_CallFunctionExpression(self, node: nodes.CallFunctionExpression):

        # Call(Access(name=my_func, struct_pointer=cls_inst))
        # cls_inst.my_func()
        if isinstance(node.value, nodes.AccessStructMember):
            method_name = node.value.name
            method_holder = node.value.struct_pointer
            method_holder_type = self.resolve_type(method_holder)

            if method_holder_type.id != TypeEnum.CLASS:
                raise GeneratorError(f"Tried calling a method from a non class value", node.location)

            class_name = method_holder_type.data['class_name']
            class_data = self.class_data[class_name]

            if method_name not in class_data.methods:
                raise GeneratorError(f"Unknown method '{method_name}' for class '{class_name}'", node.location)

            method_data = class_data.methods[method_name]
            name_mangled_name = f"__{class_name}_proc_{method_name}"
            self.functions[name_mangled_name]['called'] = True

            callee_args = method_data['arguments']
            caller_args = [method_holder] + node.args
            caller_args_len = len(caller_args)
            callee_args_len = len(callee_args)

            if caller_args_len < callee_args_len:
                raise GeneratorError(f"Too few arguments passed to method '{method_name}' for class '{class_name}'", node.location)

            if caller_args_len > callee_args_len and not method_data['varargs']:
                raise GeneratorError(f"Too many arguments passed to method '{method_name}' for class '{class_name}'", node.location)

            # Check types
            for i, (caller_value, (callee_type, _)) in enumerate(zip(caller_args, callee_args)):
                resolved_type = self.resolve_type(caller_value)
                assert resolved_type is not None, f"fail method {method_name} {i}"
                self.validate_argument(callee_type, resolved_type, method_name, i+1, node.location)

            for i, arg in reversed(list(enumerate(caller_args))):
                self._generate_node(arg)

            for i in range(min(caller_args_len, len(ARGUMENT_REGISTERS))):
                self.current_body.append(f'pop {ARGUMENT_REGISTERS[i]}')

            self.current_body.append(f'sub rsp, 32')
            self.current_body.append(f'call {name_mangled_name}')
            self.current_body.append(f'add rsp, {32 + max(caller_args_len - 4, 0) * 8}')
            self.current_body.append('push rax')

        else:
            raise GeneratorError(f"Invalid call target, must be a variable, procedure or class method", node.location)

    def _generate_ProgramExternProcedure(self, node: nodes.ProgramExternProcedure):
        self.functions[node.name] = {
            "return_type": node.return_type,
            "arguments": node.args,
            "extern": True,
            "stdcall": node.stdcall,
            "varargs": node.varargs,
            "called": False
        }

        if f'extrn {node.name}' not in self.externs:
            self.externs.append(f'extrn {node.name}')

    def _generate_ProgramExternVariable(self, node: nodes.ProgramExternVariable):
        self.globals[node.name] = {
            "type": node.type
        }

        if f'extrn {node.name}' not in self.externs:
            self.externs.append(f'extrn {node.name}')

    def _generate_Return(self, node: nodes.Return):
        if self.functions[self.current_function]['return_type'].id == TypeEnum.NONE and node.value is not None:
            raise GeneratorError(f"Cannot return a value in a function that doesn't specify a return value", node.location)

        if node.value is not None:
            self._generate_node(node.value)
            self.current_body.append('pop rax')

        self.current_body.extend([
            'mov rsp, rbp',
            'pop rbp',
            'ret'
        ])

    def _generate_ReserveUninitialized(self, node: nodes.ReserveUninitialized):
        self.bss[f"__array_{self.current_id}"] = (node.type.id, node.size)
        if self.current_body is not None:
            self.current_body.append(f'mov rax, __array_{self.current_id}')
            self.current_body.append('push rax')
        self.current_id += 1

    def _generate_ReserveInitialized(self, node: nodes.ReserveInitialized):
        data = []

        for value in node.data:
            if isinstance(value, nodes.Number):
                data.append(str(value.value))
            elif isinstance(value, nodes.String):
                if node.type.id not in [TypeEnum.PTR, TypeEnum.U64]:
                    raise GeneratorError("Reserved array type is not big enough to hold a string (u8*, u64, ptr)", value.location)

                self._generate_node(value)
                data.append(f'__str_{self.current_id-1}')
            elif isinstance(value, nodes.ReserveUninitialized):
                if node.type.id not in [TypeEnum.PTR, TypeEnum.U64]:
                    raise GeneratorError("Reserved array type is not big enough to hold a reserved array (u64, ptr)", value.location)

                self._generate_node(value)
                data.append(f'__array_{self.current_id-1}')
            elif isinstance(value, nodes.ReserveInitialized):
                if node.type.id not in [TypeEnum.PTR, TypeEnum.U64]:
                    raise GeneratorError("Reserved array type is not big enough to hold a reserved array (u64, ptr)", value.location)

                self._generate_node(value)
                data.append(f'__array_{self.current_id-1}')
            else:
                raise GeneratorError("Reserved array value must be a constant value", node.location)

        self.data[f"__array_{self.current_id}"] = (node.type.id, ','.join(data))
        if self.current_body is not None:
            self.current_body.append(f'mov rax, __array_{self.current_id}')
            self.current_body.append('push rax')
        self.current_id += 1

    def _generate_AddressOf(self, node: nodes.AddressOf):
        if node.name in self.current_locals:
            offset = self.current_locals[node.name]['offset']

            self.current_body.append(f'lea rax, [rbp - {offset}]')
            self.current_body.append('push rax')

        elif node.name in self.globals:
            self.current_body.append(f'mov rax, {node.name}')
            self.current_body.append('push rax')

        else:
            raise GeneratorError(f"undefined variable '{node.name}'", node.location)

    def _generate_DereferencePointer(self, node: nodes.DereferencePointer):
        self._generate_node(node.pointer)
        self._generate_node(node.offset)

        ptr_type = self.resolve_type(node.pointer)

        if ptr_type.id != TypeEnum.PTR:
            raise GeneratorError("Tried dereferencing a non pointer type", node.location)

        base_type = self.get_pointer_base(ptr_type)

        if not base_type:
            raise GeneratorError("Tried dereferencing a pointer with no base type", node.location)

        base_type_size = TYPE_SIZES[base_type.id]
        base_type_name = ASM_TYPE_NAMES[base_type.id]

        self.current_body.extend([
            'pop rbx',
            f'mov rax, {base_type_size}',
            'mul rbx',
            'mov rbx, rax',
            'pop rax',
            'add rax, rbx'
        ])

        if self.is_signed_16(base_type):
            self.current_body.append(f'movsx rax, {ASM_TYPE_NAMES[base_type.id]} [rax]')
            #self.current_body.append(f'movsx rax, {ASM_TYPE_NAMES[base_type.id]} [rax]')
        elif self.is_unsigned_32(base_type):
            if base_type_size != 4:
                self.current_body.append(f'mov rax, [rax]')
                self.current_body.append(f'movzx rax, {REGISTER_VARIATIONS["rax"][base_type_size]}')
            else:
                self.current_body.append("mov eax, dword [rax]")
        else:
            self.current_body.append(f'mov rax, [rax]')

        self.current_body.append(f'push rax')

    def _generate_SetAtPointer(self, node: nodes.SetAtPointer):
        self._generate_node(node.value)
        self._generate_node(node.pointer)
        self._generate_node(node.offset)

        ptr_type = self.resolve_type(node.pointer)

        if ptr_type.id != TypeEnum.PTR:
            raise GeneratorError("Tried assinging at a non pointer type", node.location)

        base_type = self.get_pointer_base(ptr_type)

        if not base_type:
            raise GeneratorError("Tried assinging at a pointer with no base type", node.location)

        base_type_size = TYPE_SIZES[base_type.id]

        self.current_body.extend([
            'pop rbx',
            f'mov rax, {base_type_size}',
            'mul rbx',
            'mov rbx, rax',
            'pop rax',
            'add rax, rbx',
            'pop rbx',
            f'mov {ASM_TYPE_NAMES[base_type.id]} [rax], {REGISTER_VARIATIONS["rbx"][TYPE_SIZES[base_type.id]]}',
            'push rbx'
        ])

    def _generate_ProgramStruct(self, node: nodes.ProgramStruct):
        self.struct_data[node.name] = self.calculate_struct(node.members)

    def _generate_ProgramClass(self, node: nodes.ProgramClass):
        self.struct_data[node.name] = self.calculate_struct(node.members)
        self.class_data[node.name] = node

    def _generate_Enumeration(self, node: nodes.Enumeration):
        self.enum_data[node.name] = node.values

    def calculate_struct(self, substruct_fields):
        # calculate padded size of the struct
        # calculate offsets of each memeber
        fields = {}

        max_align = 1
        width_sum = 0

        for field_type, field_name in substruct_fields:
            type_size = None
            padding = 0

            if field_type.id == TypeEnum.SUB_STRUCT:
                sub_data = self.calculate_struct(field_type.data['fields'])
                type_size = sub_data['size']

                if sub_data['largest_size'] > max_align:
                    max_align = sub_data['largest_size']

                field_type.data = sub_data

            elif field_type.id == TypeEnum.ARRAY:
                element_type_size = TYPE_SIZES[field_type.data['element_type'].id]
                array_size = element_type_size * field_type.data['size']

                if element_type_size > max_align:
                    max_align = element_type_size

                # width_sum += array_size
                remainder = width_sum % element_type_size

                if width_sum > 0 and remainder != 0:
                    padding = element_type_size - remainder

                type_size = array_size

            else:
                type_size = TYPE_SIZES[field_type.id]
                if type_size > max_align:
                    max_align = type_size

                remainder = width_sum % type_size

                if width_sum > 0 and remainder != 0:
                    padding = type_size - remainder

            offset = width_sum + padding
            fields[field_name] = {
                "offset": offset,
                "size": type_size,
                "type": field_type
            }

            padded_size = type_size + padding
            width_sum += padded_size

        rem = width_sum % max_align
        if rem != 0:
            width_sum += max_align - rem

        return {
            "fields": fields,
            "size": width_sum,
            "largest_size": max_align
        }

    def _generate_AccessStructMember(self, node: nodes.AccessStructMember):
        if isinstance(node.struct_pointer, nodes.Variable):
            if node.struct_pointer.name in self.enum_data:
                enum_data = self.enum_data[node.struct_pointer.name]
                if node.name not in enum_data:
                    raise GeneratorError(f"Unknown enum value '{node.name}' in enum '{node.struct_pointer.name}'", node.location)

                self.current_body.extend([
                    f'mov rax, {enum_data[node.name]}',
                    'push rax'
                ])

                return

        self._generate_node(node.struct_pointer)

        struct_type = self.resolve_type(node.struct_pointer)
        members = None

        if struct_type.id == TypeEnum.STRUCT:
            struct_name = struct_type.data['struct_name']
            members = self.struct_data[struct_name]['fields']

        elif struct_type.id == TypeEnum.CLASS:
            struct_name = struct_type.data['class_name']
            members = self.struct_data[struct_name]['fields']

        elif struct_type.id == TypeEnum.SUB_STRUCT:
            members = struct_type.data['fields']

        else:
            raise GeneratorError("Attempted field access on a non struct type", node.location)

        field_offset = None
        field_type = None

        if node.name not in members:
            raise GeneratorError(f"Unknown field '{node.name}'", node.location)

        field_offset, field_type = members[node.name]['offset'], members[node.name]['type']

        if field_type.id in [TypeEnum.SUB_STRUCT, TypeEnum.ARRAY]:
            self.current_body.extend([
                'pop rax',
                f'add rax, {field_offset}',
                'push rax'
            ])

            return

        field_size = TYPE_SIZES[field_type.id]

        self.current_body.extend([
            'pop rax',
            f'add rax, {field_offset}',
            #f'{("movsx" if self.is_signed_32(field_type) else "movzx") if field_size != 8 else "mov"} rax, {ASM_TYPE_NAMES[field_type.id]} [rax]',
            #'push rax'
        ])

        if self.is_signed_16(field_type):
            self.current_body.append(f'movsx rax, {ASM_TYPE_NAMES[field_type.id]} [rax]')
        elif self.is_unsigned_32(field_type):
            if TYPE_SIZES[field_type.id] != 4:
                self.current_body.append(f'mov rax, [rax]')
                self.current_body.append(f'movzx rax, {REGISTER_VARIATIONS["rax"][TYPE_SIZES[field_type.id]]}')
            else:
                self.current_body.append("mov eax, dword [rax]")
        else:
            self.current_body.append(f'mov rax, [rax]')

        self.current_body.append(f'push rax')

    def _generate_WriteStructMember(self, node: nodes.WriteStructMember):
        self._generate_node(node.struct_pointer)

        struct_type = self.resolve_type(node.struct_pointer)
        members = None

        if struct_type.id == TypeEnum.STRUCT:
            struct_name = struct_type.data['struct_name']
            members = self.struct_data[struct_name]['fields']

        elif struct_type.id == TypeEnum.CLASS:
            struct_name = struct_type.data['class_name']
            members = self.struct_data[struct_name]['fields']

        elif struct_type.id == TypeEnum.SUB_STRUCT:
            members = struct_type.data['fields']

        else:
            raise GeneratorError("Attempted field access on a non struct type", node.location)

        field_offset = None
        field_type = None

        if node.name not in members:
            raise GeneratorError(f"Unknown field '{node.name}'", node.location)

        field_offset, field_type = members[node.name]['offset'], members[node.name]['type']
        field_size = TYPE_SIZES[field_type.id]

        self._generate_node(node.value)

        if field_type.id == TypeEnum.SUB_STRUCT:
            raise GeneratorError("Attempted assigning to a sub struct", node.location)

        self.current_body.extend([
            'pop rbx',
            'pop rax',
            f'add rax, {field_offset}',
            f'mov {ASM_TYPE_NAMES[field_type.id]} [rax], {REGISTER_VARIATIONS["rbx"][field_size]}',
            'push rax'
        ])

    def _generate_Sizeof(self, node: nodes.Sizeof):
        value_type = self.resolve_type(node.value)
        self.current_body.append(f"push {TYPE_SIZES[value_type.id]}")

    def _generate_SizeofType(self, node: nodes.SizeofType):
        if node.type.id == TypeEnum.STRUCT:
            self.current_body.append(f"push {self.struct_data[node.type.data['struct_name']]['size']}")
            return

        if node.type.id == TypeEnum.CLASS:
            self.current_body.append(f"push {self.struct_data[node.type.data['class_name']]['size']}")
            return

        if node.type.id == TypeEnum.SUB_STRUCT:
            struct_data = self.calculate_struct(node.type.data['fields'])
            self.current_body.append(f"push {struct_data['size']}")
            return

        self.current_body.append(f"push {TYPE_SIZES[node.type.id]}")

    def _generate_Negate(self, node: nodes.Negate):
        self._generate_node(node.value)
        self.current_body.extend([
            'pop rax',
            'cmp rax, 0',
            'sete al',
            'movzx rax, al',
            'push rax'
        ])

    def _generate_CompoundStatement(self, node: nodes.CompoundStatement):
        self.old_locals = self.current_locals
        self.current_locals = LocalDict(self.current_locals)

        for statement in node.body:
            self._generate_node(statement)

        self.current_locals = self.old_locals

    def _generate_IfStatement(self, node: nodes.IfStatement):
        self._generate_node(node.value)
        self.current_body.append('pop rax')
        self.current_body.append('cmp rax, 0')
        jmp_idx = len(self.current_body)
        else_idx = 0
        self.current_body.append('je SOME_ADDRESS')

        self._generate_node(node.body)
        
        if node.else_body:
            else_idx = len(self.current_body)
            self.current_body.append('je SOME_ADDRESS')

        self.current_body.append(f'.L{self.current_label}:')

        self.current_body[jmp_idx] = f"je .L{self.current_label}"
        self.current_label += 1

        if node.else_body:
            self._generate_node(node.else_body)
            self.current_body.append(f'.L{self.current_label}:')
            self.current_body[else_idx] = f"jmp .L{self.current_label}"
            self.current_label += 1


    def _generate_WhileStatement(self, node: nodes.WhileStatement):
        while_label = self.current_label
        self.current_body.append(f'.L{while_label}:')
        self.current_label += 1

        self._generate_node(node.value)
        self.current_body.append('pop rax')
        self.current_body.append('cmp rax, 0')
        next_label = self.current_label
        self.current_body.append(f'je .L{next_label}')
        self.current_label += 1
        self.break_stack.append(f".L{next_label}")

        self._generate_node(node.body)
        self.current_body.append(f'jmp .L{while_label}')

        self.current_body.append(f'.L{next_label}:')
        self.break_stack.pop()

    def _generate_BreakLoop(self, node: nodes.BreakLoop):
        if not self.break_stack:
            raise GeneratorError("Cannot use break outside of loops", node.location)

        self.current_body.append(f"jmp {self.break_stack[-1]}")

    def _generate_NewInstance(self, node: nodes.NewInstance):
        if node.name not in self.class_data:
            raise GeneratorError(f"Unknown class '{node.name}'", node.location)

        class_data = self.class_data[node.name]
        method_data = class_data.initializer
        class_name = node.name
        name_mangled_name = f"__{class_name}_init_"

        type_size = 8 # size of ptr

        # allocate temp local variable
        if type_size > self.max_align:
            self.max_align = type_size

        padding = 0
        remainder = self.local_offset % type_size

        if self.local_offset > 0 and remainder != 0:
            padding = type_size - remainder

        padded_size = type_size + padding
        self.local_offset += padded_size
        temp_offset = self.local_offset

        self.current_body.extend([
            f"mov rcx, {self.struct_data[class_name]['size']}",
            #"push rcx",
            "sub rsp, 32",
            "call malloc",
            "add rsp, 32",
            #"pop rax",
            f"mov qword [rbp - {temp_offset}], rax"
        ])

        callee_args = method_data['arguments'][1:]
        caller_args = node.args
        caller_args_len = len(caller_args)
        callee_args_len = len(callee_args)

        if caller_args_len < callee_args_len:
            raise GeneratorError(f"Too few arguments passed to initializer for class '{class_name}'", node.location)

        if caller_args_len > callee_args_len and not method_data['varargs']:
            raise GeneratorError(f"Too many arguments passed to initializer for class '{class_name}'", node.location)

        # Check types
        for i, (caller_value, (callee_type, _)) in enumerate(zip(caller_args, callee_args)):
            resolved_type = self.resolve_type(caller_value)
            assert resolved_type is not None, f"fail initializer {i}"
            self.validate_argument(callee_type, resolved_type, "initializer", i+1, node.location)

        for i, arg in reversed(list(enumerate(caller_args))):
            self._generate_node(arg)

        self.current_body.append(f"mov rcx, qword [rbp - {temp_offset}]")

        for i in range(min(caller_args_len, len(ARGUMENT_REGISTERS)-1)):
            self.current_body.append(f'pop {ARGUMENT_REGISTERS[i+1]}')

        self.current_body.append('sub rsp, 32')
        self.current_body.append(f'call {name_mangled_name}')
        self.current_body.append(f'add rsp, {32 + max(caller_args_len - 4, 0) * 8}')

        self.current_body.append(f"mov rax, qword [rbp - {temp_offset}]")
        self.current_body.append(f"push rax")

    def _generate_Register(self, node: nodes.Register):
        self.current_body.append(f'push {node.name}')

    def _generate_AssignRegister(self, node: nodes.AssignRegister):
        self._generate_node(node.value)
        self.current_body.append(f'pop {node.name}')

    def _generate_Multiple(self, node: nodes.Multiple):
        for n in node.nodes:
            self._generate_node(n)

    def _generate_SwitchStatement(self, node: nodes.SwitchStatement):
        end_label = f".L{self.current_label}"
        self.current_label += 1
        self.break_stack.append(end_label)

        default_label = None
        if node.default_case:
            default_label = f".L{self.current_label}"
            self.current_label += 1

        self._generate_node(node.value)
        self.current_body.append('pop rax')

        case_labels = []
        # generate checks
        for (case_const, _) in node.cases:
            case_labels.append(self.current_label)
            self.current_body.extend([
                f'cmp rax, {case_const}',
                f'je .L{self.current_label}'
            ])
            self.current_label += 1

        if node.default_case:
            self.current_body.append(f"jmp {default_label}")
        else:
            self.current_body.append(f"jmp {end_label}")

        # generate cases

        for i, (_, case_body) in enumerate(node.cases):
            self.current_body.append(f".L{case_labels[i]}:")
            for case_node in case_body:
                self._generate_node(case_node)

        if node.default_case:
            self.current_body.append(f"{default_label}:")
            for def_node in node.default_case:
                self._generate_node(def_node)

        self.current_body.append(f"{end_label}:")
        self.break_stack.pop()

    def _generate_Call(self, node: nodes.Call):
        func_name = node.name

        if func_name not in self.functions:
            raise GeneratorError(f"Tried calling an undefined function '{func_name}'", node.location)

        callee_args = self.functions[func_name]['arguments']
        callee_args_len = len(callee_args) if node.args_passed == 0 else node.args_passed
        self.functions[func_name]['called'] = True
 
        for i in range(min(callee_args_len, len(ARGUMENT_REGISTERS))):
            self.current_body.append(f'pop {ARGUMENT_REGISTERS[i]}')

        self.current_body.append(f'sub rsp, 32')
        self.current_body.append(f'call {func_name}')
        self.current_body.append(f'add rsp, {32 + max(callee_args_len - 4, 0) * 8}')
        self.current_body.append('push rax')

    def _generate_Push(self, node: nodes.Push):
        self._generate_node(node.value)

    def _generate_Pop(self, node: nodes.Pop):
        if node.name is not None:
            if node.name in self.current_locals:
                var_type = self.current_locals[node.name]['type']
                offset = self.current_locals[node.name]['offset']
                type_size, type_name = TYPE_SIZES[var_type.id], ASM_TYPE_NAMES[var_type.id]

                self.current_body.append('pop rax')
                self.current_body.append(f'mov {type_name.lower()} [rbp - {offset}], {REGISTER_VARIATIONS["rax"][type_size]}')

            elif node.name in self.globals:
                var_type = self.globals[node.name]['type']
                type_size, type_name = TYPE_SIZES[var_type.id], ASM_TYPE_NAMES[var_type.id]

                self.current_body.append('pop rax')
                self.current_body.append(f'mov {type_name.lower()} [{node.name}], {REGISTER_VARIATIONS["rax"][type_size]}')

        else:
            self.current_body.append('add rsp, 8')

    def _generate_InlineAssembly(self, node: nodes.InlineAssembly):
        self.current_body.append(node.value)

    def resolve_type(self, expr) -> nodes.Type:
        if isinstance(expr, nodes.Number):
            return nodes.Type(TypeEnum.I64)

        elif isinstance(expr, nodes.String):
            return nodes.Type(TypeEnum.PTR)

        elif isinstance(expr, nodes.Variable):
            if expr.name in self.current_locals:
                return self.current_locals[expr.name]['type']
            
            elif expr.name in self.globals:
                return self.globals[expr.name]['type']
            
            raise GeneratorError(f"Undefined variable '{expr.name}'", expr.location)

        elif isinstance(expr, nodes.AssignVariable):
            if expr.name in self.current_locals:
                return self.current_locals[expr.name]['type']
            
            elif expr.name in self.globals:
                return self.globals[expr.name]['type']
            
            raise GeneratorError(f"Attempted assinging to an undefined variable '{expr.name}'", expr.location)

        elif isinstance(expr, nodes.BinaryOperation):
            left_type = self.resolve_type(expr.left)
            right_type = self.resolve_type(expr.right)

            left_size = TYPE_SIZES[left_type.id]
            right_size = TYPE_SIZES[right_type.id]

            if expr.operation in [TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH, TokenType.AND, TokenType.ARROW_UP, TokenType.PIPE, TokenType.AMPERSAND]:
                return left_type if left_size > right_size else right_type

            elif expr.operation in [TokenType.PRECENT, TokenType.NEQUALS, TokenType.LEQUALS, TokenType.GEQUALS, TokenType.GREATER, TokenType.LOWER, TokenType.DEQUALS, TokenType.AND, TokenType.OR]:
                return nodes.Type(id=TypeEnum.U8)

        elif isinstance(expr, nodes.CallFunction):
            if expr.name not in self.functions:
                raise GeneratorError(f"Tried calling an undefined function '{expr.name}'", expr.location)

            func_data = self.functions[expr.name]
            return func_data['return_type']

        elif isinstance(expr, nodes.CallFunctionExpression):
            if isinstance(expr.value, nodes.AccessStructMember):
                method_name = expr.value.name
                method_holder = expr.value.struct_pointer
                method_holder_type = self.resolve_type(method_holder)

                if method_holder_type.id != TypeEnum.CLASS:
                    raise GeneratorError(f"Tried calling a method from a non class value", expr.location)

                class_name = method_holder_type.data['class_name']
                class_data = self.class_data[class_name]

                if method_name not in class_data.methods:
                    raise GeneratorError(f"Unknown method '{method_name}' for class '{class_name}'", expr.location)

                method_data = class_data.methods[method_name]
                return method_data['return_type']
            else:
                raise GeneratorError(f"Invalid call target, must be a variable, procedure or class method", expr.location)

        elif isinstance(expr, nodes.Cast):
            return expr.type

        elif isinstance(expr, nodes.DereferencePointer):
            ptr_type = self.resolve_type(expr.pointer)
            base_type = self.get_pointer_base(ptr_type)

            if not base_type:
                raise GeneratorError("Tried dereferencing a pointer with no base type", expr.location)

            return base_type

        elif isinstance(expr, nodes.SetAtPointer):
            ptr_type = self.resolve_type(expr.pointer)
            base_type = self.get_pointer_base(ptr_type)

            if not base_type:
                return nodes.Type(id=TypeEnum.PTR)

            return nodes.Type(id=TypeEnum.PTR, is_base_type=False, base_type=base_type)

        elif isinstance(expr, nodes.Cast):
            return expr.type

        elif isinstance(expr, nodes.AddressOf):
            base_type = None

            if expr.name in self.current_locals:
                base_type = self.current_locals[expr.name]['type']
            
            elif expr.name in self.globals:
                base_type = self.globals[expr.name]['type']

            if not base_type:
                raise Exception("Unreacahble")

            return nodes.Type(id=TypeEnum.PTR, is_base_type=False, base_type=base_type)

        elif isinstance(expr, (nodes.ReserveUninitialized, nodes.ReserveInitialized)):
            return nodes.Type(id=TypeEnum.PTR, is_base_type=False, base_type=expr.type)

        elif isinstance(expr, nodes.AccessStructMember):
            if isinstance(expr.struct_pointer, nodes.Variable):
                if expr.struct_pointer.name in self.enum_data:
                    enum_data = self.enum_data[expr.struct_pointer.name]
                    if expr.name not in enum_data:
                        raise GeneratorError(f"Unknown enum value '{expr.name}' in enum '{expr.struct_pointer.name}'", expr.location)

                    return nodes.Type(id=TypeEnum.U64)

            struct_type = self.resolve_type(expr.struct_pointer)
            members = None

            if struct_type.id == TypeEnum.STRUCT:
                struct_name = struct_type.data['struct_name']
                members = self.struct_data[struct_name]['fields']

            elif struct_type.id == TypeEnum.CLASS:
                struct_name = struct_type.data['class_name']
                members = self.struct_data[struct_name]['fields']

            elif struct_type.id == TypeEnum.SUB_STRUCT:
                members = struct_type.data['fields']

            else:
                raise GeneratorError("Attempted field access on a non struct type", expr.location)

            if expr.name in members:
                field_type = members[expr.name]['type']

                if field_type.id == TypeEnum.ARRAY:
                    return nodes.Type(id=TypeEnum.PTR, is_base_type=False, base_type=field_type.data['element_type'])

                return field_type
            
            raise GeneratorError(f"Unknown field '{expr.name}'", expr.location)

        elif isinstance(expr, nodes.WriteStructMember):
            struct_type = self.resolve_type(expr.struct_pointer)
            members = None

            if struct_type.id == TypeEnum.STRUCT:
                struct_name = struct_type.data['struct_name']
                members = self.struct_data[struct_name]['fields']

            elif struct_type.id == TypeEnum.CLASS:
                struct_name = struct_type.data['class_name']
                members = self.struct_data[struct_name]['fields']

            elif struct_type.id == TypeEnum.SUB_STRUCT:
                members = struct_type.data['fields']

            else:
                raise GeneratorError("Attempted struct field access on a non struct type", expr.location)

            if expr.name in members:
                return members[expr.name]['type']
            
            raise GeneratorError(f"Unknown struct field '{expr.name}'", expr.location)

        elif isinstance(expr, nodes.Sizeof):
            return nodes.Type(id=TypeEnum.U64)

        elif isinstance(expr, nodes.SizeofType):
            return nodes.Type(id=TypeEnum.U64)

        elif isinstance(expr, nodes.NewInstance):
            if expr.name not in self.class_data:
                raise GeneratorError(f"Unknown class '{expr.name}'", expr.location)

            return nodes.Type(id=TypeEnum.CLASS, data={'class_name': expr.name})

        elif isinstance(expr, nodes.Register):
            return nodes.Type(id=TypeEnum.U64)

        elif isinstance(expr, nodes.AssignRegister):
            return nodes.Type(id=TypeEnum.U64)

    def get_pointer_base(self, ptr_type: nodes.Type):
        if ptr_type.id == TypeEnum.PTR and not ptr_type.is_base_type:
            return ptr_type.base_type

        return None

    def validate_argument(self, expected: nodes.Type, given: nodes.Type, func_name: str, parameter_id: int, location: TokenLocation):
        if expected.id == TypeEnum.PTR and given.id == TypeEnum.PTR:
            return True
            
        if expected.id == TypeEnum.STRUCT and given.id == TypeEnum.STRUCT:
            if expected.data['struct_name'] == given.data['struct_name']:
                return True

        if expected.id == TypeEnum.CLASS and given.id == TypeEnum.CLASS:
            if expected.data['class_name'] == given.data['class_name']:
                return True

        if expected.id == TypeEnum.SUB_STRUCT and given.id == TypeEnum.SUB_STRUCT:
            return True

        if self.is_numeric_type(expected) and self.is_numeric_type(given):
            return True

        raise GeneratorError(f"Passed wrong type of parameter to function '{func_name}', parameter #{parameter_id} expected '{self.get_type_name(expected)}', but got '{self.get_type_name(given)}'", location)

    def validate_type(self, expected: nodes.Type, given: nodes.Type, location: TokenLocation, format: str, *args):
        if expected.id == TypeEnum.PTR and given.id == TypeEnum.PTR:
            return True

        if expected.id == TypeEnum.STRUCT and given.id == TypeEnum.STRUCT:
            if expected.data['struct_name'] == given.data['struct_name']:
                return True

        if expected.id == TypeEnum.CLASS and given.id == TypeEnum.CLASS:
            if expected.data['class_name'] == given.data['class_name']:
                return True

        if expected.id == TypeEnum.SUB_STRUCT and given.id == TypeEnum.SUB_STRUCT:
            return True

        if self.is_numeric_type(expected) and self.is_numeric_type(given):
            return True
            
        raise GeneratorError(format.format(*args), location)

    def is_numeric_type(self, type_: nodes.Type):
        return type_.id in [TypeEnum.U8, TypeEnum.U16, TypeEnum.U32, TypeEnum.U64, TypeEnum.I8, TypeEnum.I16, TypeEnum.I32, TypeEnum.I64]

    def is_signed(self, type_: nodes.Type):
        return type_.id in [TypeEnum.I8, TypeEnum.I16, TypeEnum.I32, TypeEnum.I64]

    def is_signed_32(self, type_: nodes.Type):
        return type_.id in [TypeEnum.I8, TypeEnum.I16, TypeEnum.I32]

    def is_signed_16(self, type_: nodes.Type):
        return type_.id in [TypeEnum.I8, TypeEnum.I16]

    def is_unsigned_32(self, type_: nodes.Type):
        return type_.id in [TypeEnum.U8, TypeEnum.U16, TypeEnum.U32]

    def get_type_name(self, type_: nodes.Type):
        if type_.id == TypeEnum.STRUCT:
            return type_.data['struct_name']
        
        if type_.id == TypeEnum.CLASS:
            return type_.data['class_name']

        return TYPE_NAMES[type_.id]

class GeneratorError(Exception):
    def __init__(self, msg, location: TokenLocation) -> None:
        self.msg = msg
        self.location = location

    def __repr__(self) -> str:
        return "%s:%d:%d: [ERROR]: %s" % (self.location + (self.msg,))

    def __str__(self) -> str:
        return "%s:%d:%d: [ERROR]: %s" % (self.location + (self.msg,))