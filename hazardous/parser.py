from typing import List
from .scanner import Token, TokenLocation, TokenType
from . import nodes


TOKEN_VAR_TYPE = {
    TokenType.U8: nodes.TypeEnum.U8,
    TokenType.U16: nodes.TypeEnum.U16,
    TokenType.U32: nodes.TypeEnum.U32,
    TokenType.U64: nodes.TypeEnum.U64,
    TokenType.I8: nodes.TypeEnum.I8,
    TokenType.I16: nodes.TypeEnum.I16,
    TokenType.I32: nodes.TypeEnum.I32,
    TokenType.I64: nodes.TypeEnum.I64,
    TokenType.PTR: nodes.TypeEnum.PTR
}


class Parser:
    def parse(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.typedefs = {}
        self.enum_data = {}

        declarations = []

        while self.available():
            node = self.parse_declarations()
            if node:
                if isinstance(node, list):
                    declarations.extend(node)
                else:
                    declarations.append(node)

        for type_name, type_data in self.typedefs.items():
            if type_data.id in [nodes.TypeEnum.STRUCT, nodes.TypeEnum.CLASS]:
                if not type_data.data['declared']:
                    self.error(type_data.data['location'], f"Body of '{type_name}' was never defined, only forward declared")

        return declarations

    def parse_declarations(self):
        is_local = self.match(TokenType.LOCAL)

        if self.match(TokenType.VAR):
            var_name = self.consume(TokenType.IDENTIFIER, "Expected variable name")
            self.consume(TokenType.COLON, "Expected variable type")
            var_type = self.consume_type("Expected variable type")
            # var_value = self.parse_constant() if self.match(TokenType.EQUALS) else None
            self.consume(TokenType.SEMICOLON, "Expected ';' after global variable declaration")

            return nodes.ProgramVariable(name=var_name.value, type=var_type, is_local=is_local, location=var_name.location)

        if self.match(TokenType.PROC):
            stdcall = self.match(TokenType.STDCALL)
            name = self.consume(TokenType.IDENTIFIER, "Expected procedure name")
            args = []
            varargs = False

            if self.match(TokenType.OPEN_PAREN):
                if not self.check(TokenType.CLOSE_PAREN):
                    while True:
                        if self.match(TokenType.VARARGS):
                            varargs = True
                            break

                        arg_name = self.consume(TokenType.IDENTIFIER, "Expected procedure parameter name")
                        self.consume(TokenType.COLON, "Expected procedure parameter type")
                        arg_type = self.consume_type("Expected procedure parameter type")
                        args.append((arg_type, arg_name.value))

                        if not self.match(TokenType.COMMA): break

                self.consume(TokenType.CLOSE_PAREN, "Expected ')' after procedure parameters")

            return_type = self.consume_type("Expected procedure return type after '->'") if self.match(TokenType.POINTER_ARROW) else nodes.Type(id=nodes.TypeEnum.NONE)
            
            if self.match(TokenType.SEMICOLON):
                return nodes.ProgramProcedure(name=name.value, location=name.location, is_local=is_local, stdcall=stdcall, args=args, return_type=return_type, body=None, varargs=varargs, forward_declared=True)
            
            self.consume(TokenType.OPEN_BRACE, "Expected '{' for procedure body")
            body = self.parse_block()

            return nodes.ProgramProcedure(name=name.value, location=name.location, is_local=is_local, stdcall=stdcall, args=args, return_type=return_type, body=body, varargs=varargs, forward_declared=False)

        if self.match(TokenType.EXTERNAL):
            if self.match(TokenType.PROC):
                stdcall = self.match(TokenType.STDCALL)
                name = self.consume(TokenType.IDENTIFIER, "Expected procedure name")
                args = []
                varargs = False

                if self.match(TokenType.OPEN_PAREN):
                    if not self.check(TokenType.CLOSE_PAREN):
                        while True:
                            if self.match(TokenType.VARARGS):
                                varargs = True
                                break

                            arg_name = self.consume(TokenType.IDENTIFIER, "Expected procedure parameter name")
                            self.consume(TokenType.COLON, "Expected procedure parameter type")
                            arg_type = self.consume_type("Expected procedure parameter type")
                            args.append((arg_type, arg_name.value))

                            if not self.match(TokenType.COMMA): break

                    self.consume(TokenType.CLOSE_PAREN, "Expected ')' after procedure parameters")

                return_type = self.consume_type("Expected procedure return type after '->'") if self.match(TokenType.POINTER_ARROW) else nodes.Type(id=nodes.TypeEnum.NONE)
                self.consume(TokenType.SEMICOLON, "Expected ';' after extern procedure")

                return nodes.ProgramExternProcedure(name=name.value, location=name.location, stdcall=stdcall, args=args, return_type=return_type, varargs=varargs)

            if self.match(TokenType.VAR):
                var_name = self.consume(TokenType.IDENTIFIER, "Expected variable name")
                self.consume(TokenType.COLON, "Expected variable type")
                var_type = self.consume_type("Expected variable type")
                self.consume(TokenType.SEMICOLON, "Expected ';' after extern variable declaration")
                return nodes.ProgramExternVariable(name=var_name.value, location=var_name.location, type=var_type)

        if self.match(TokenType.STRUCT):
            name = self.consume(TokenType.IDENTIFIER, "Expected struct name")

            if self.match(TokenType.SEMICOLON):
                self.typedefs[name.value] = nodes.Type(id=nodes.TypeEnum.STRUCT, data={"struct_name": name.value, "declared": False, "location": name.location})
                return

            body = self.parse_sub_struct()

            self.typedefs[name.value] = nodes.Type(id=nodes.TypeEnum.STRUCT, data={"struct_name": name.value, "declared": True})
            return nodes.ProgramStruct(name=name.value, members=body, location=name.location)

        if self.match(TokenType.ENUM):
            name = self.consume(TokenType.IDENTIFIER, "Expected enum name")

            self.consume(TokenType.OPEN_BRACE, "Expected '{'")

            enums = {}
            num = 0

            if not self.check(TokenType.CLOSE_BRACE):
                while True:
                    enum_name = self.consume(TokenType.IDENTIFIER, "Expected enumeration value name")

                    if self.match(TokenType.EQUALS):
                        tok = self.consume(TokenType.NUMBER, "Expected number after '=' in enum")
                        num = int(tok.value)

                    enums[enum_name.value] = num
                    num += 1
                    
                    if not self.match(TokenType.COMMA): break

            self.consume(TokenType.CLOSE_BRACE, "Expected '}'")
            self.typedefs[name.value] = nodes.Type(id=nodes.TypeEnum.U64)
            self.enum_data[name.value] = enums
            return nodes.Enumeration(name=name.value, values=enums)

        if self.match(TokenType.CLASS):
            name = self.consume(TokenType.IDENTIFIER, "Expected class name")

            if self.match(TokenType.SEMICOLON):
                self.typedefs[name.value] = nodes.Type(id=nodes.TypeEnum.CLASS, data={"class_name": name.value, "declared": False, "location": name.location})
                return

            self.consume(TokenType.OPEN_BRACE, "Expected '{'")

            body = []
            methods = {}
            returned_nodes = []
            initializer = None

            while not self.check(TokenType.CLOSE_BRACE):
                if self.match(TokenType.VAR):
                    field_name = self.consume(TokenType.IDENTIFIER, "Expected field name")
                    self.consume(TokenType.COLON, "Expected field type")
                    field_type = self.consume_type("Expected field type")

                    if self.match(TokenType.OPEN_SQUARE):
                        arr_size = self.consume(TokenType.NUMBER, "Expected array size").value
                        self.consume(TokenType.CLOSE_SQUARE, "Expected ']' after array size")
                        field_type = nodes.Type(id=nodes.TypeEnum.ARRAY, data={"size": int(arr_size), "element_type": field_type})

                    self.consume(TokenType.SEMICOLON, "Expected ';' after field")

                    body.append((field_type, field_name.value))

                elif self.match(TokenType.PROC):
                    method_name = self.consume(TokenType.IDENTIFIER, "Expected method name")
                    args = [(nodes.Type(id=nodes.TypeEnum.CLASS, data={"class_name": name.value, "declared": True}), "this")]
                    varargs = False

                    if self.match(TokenType.OPEN_PAREN):
                        if not self.check(TokenType.CLOSE_PAREN):
                            while True:
                                if self.match(TokenType.VARARGS):
                                    varargs = True
                                    break

                                arg_name = self.consume(TokenType.IDENTIFIER, "Expected method parameter name")
                                self.consume(TokenType.COLON, "Expected method parameter type")
                                arg_type = self.consume_type("Expected method parameter type")
                                args.append((arg_type, arg_name.value))

                                if not self.match(TokenType.COMMA): break

                        self.consume(TokenType.CLOSE_PAREN, "Expected ')' after method parameters")

                    return_type = self.consume_type("Expected method return type after '->'") if self.match(TokenType.POINTER_ARROW) else nodes.Type(id=nodes.TypeEnum.NONE)
                    
                    if self.match(TokenType.SEMICOLON):
                        returned_nodes.append(nodes.ProgramProcedure(name=f"__{name.value}_proc_{method_name.value}", return_type=return_type, body=func_body, args=args, location=method_name.location, forward_declared=True, varargs=varargs, stdcall=False, is_local=True))
                    else:
                        self.consume(TokenType.OPEN_BRACE, "Expected '{' for method body")
                        func_body = self.parse_block()

                        methods[method_name.value] = {"arguments": args, "varargs": varargs, "return_type": return_type}
                        returned_nodes.append(nodes.ProgramProcedure(name=f"__{name.value}_proc_{method_name.value}", return_type=return_type, body=func_body, args=args, location=method_name.location, forward_declared=False, varargs=varargs, stdcall=False, is_local=True))

                # initializer
                elif self.peek().type == TokenType.IDENTIFIER and self.peek().value == name.value:
                    init_token = self.advance()
                    args = [(nodes.Type(id=nodes.TypeEnum.CLASS, data={"class_name": name.value, "declared": True}), "this")]
                    varargs = False

                    if self.match(TokenType.OPEN_PAREN):
                        if not self.check(TokenType.CLOSE_PAREN):
                            while True:
                                if self.match(TokenType.VARARGS):
                                    varargs = True
                                    break

                                arg_name = self.consume(TokenType.IDENTIFIER, "Expected method parameter name")
                                self.consume(TokenType.COLON, "Expected method parameter type")
                                arg_type = self.consume_type("Expected method parameter type")
                                args.append((arg_type, arg_name.value))

                                if not self.match(TokenType.COMMA): break

                        self.consume(TokenType.CLOSE_PAREN, "Expected ')' after method parameters")

                    self.consume(TokenType.OPEN_BRACE, "Expected '{' for method body")
                    func_body = self.parse_block()

                    initializer = {"arguments": args, "varargs": varargs}
                    returned_nodes.append(nodes.ProgramProcedure(name=f"__{name.value}_init_", return_type=nodes.Type(id=nodes.TypeEnum.NONE), body=func_body, args=args, location=init_token.location, forward_declared=False, varargs=varargs, stdcall=False, is_local=True, always=True))

                else:
                    self.error(self.peek().location, "Expected class member, function or initializer")

            self.consume(TokenType.CLOSE_BRACE, "Expected '}'")

            self.typedefs[name.value] = nodes.Type(id=nodes.TypeEnum.CLASS, data={"class_name": name.value, "declared": True})
            returned_nodes.insert(0, nodes.ProgramClass(name=name.value, members=body, methods=methods, location=name.location, initializer=initializer))
            return returned_nodes

        if not self.match(TokenType.EOF):
            self.error(self.peek().location, "Expected declaration")

    def parse_sub_struct(self):
        self.consume(TokenType.OPEN_BRACE, "Expected '{'")

        body = []

        while not self.check(TokenType.CLOSE_BRACE):
            field_name = self.consume(TokenType.IDENTIFIER, "Expected field name")
            self.consume(TokenType.COLON, "Expected field type")
            field_type = self.consume_type("Expected field type")

            if self.match(TokenType.OPEN_SQUARE):
                arr_size = self.consume(TokenType.NUMBER, "Expected array size").value
                self.consume(TokenType.CLOSE_SQUARE, "Expected ']' after array size")
                field_type = nodes.Type(id=nodes.TypeEnum.ARRAY, data={"size": int(arr_size), "element_type": field_type})

            self.consume(TokenType.SEMICOLON, "Expected ';' after field")

            body.append((field_type, field_name.value))

        self.consume(TokenType.CLOSE_BRACE, "Expected '}'")

        return body

    def parse_block(self):
        statements = []

        while not self.check(TokenType.CLOSE_BRACE):
            statements.append(self.parse_statement())

        self.consume(TokenType.CLOSE_BRACE, "Expected '}' after code block")
        return statements

    def parse_statement(self):
        if self.match(TokenType.VAR):
            var_name = self.consume(TokenType.IDENTIFIER, "Expected variable name")
            # auto type
            if self.match(TokenType.EQUALS):
                var_value = self.parse_expression()
                self.consume(TokenType.SEMICOLON, "Expected ';' after local variable declaration")
                return nodes.LocalVariable(name=var_name.value, location=var_name.location, type=None, value=var_value)

            self.consume(TokenType.COLON, "Expected variable type")
            var_type = self.consume_type("Expected variable type")

            if self.match(TokenType.OPEN_SQUARE):
                size = self.consume(TokenType.NUMBER, "Expected array size")
                self.consume(TokenType.CLOSE_SQUARE, "Expected ']' after local array size")
                self.consume(TokenType.SEMICOLON, "Expected ';' after local variable declaration")
                return nodes.LocalArray(name=var_name.value, type=var_type, size=int(size.value), location=var_name.location)

            if var_type.id == nodes.TypeEnum.STRUCT and self.match(TokenType.SEMICOLON):
                return nodes.LocalStruct(name=var_name.value, type=var_type, location=var_name.location)

            if var_type.id == nodes.TypeEnum.CLASS:
                if self.match(TokenType.SEMICOLON):
                    return nodes.LocalStruct(name=var_name.value, type=var_type, location=var_name.location)
                
                if self.match(TokenType.OPEN_PAREN):
                    args = [nodes.Variable(name=var_name.value, location=var_name.location)]
                    if not self.check(TokenType.CLOSE_PAREN):
                        while True:
                            args.append(self.parse_expression())
                            if not self.match(TokenType.COMMA): break

                    self.consume(TokenType.CLOSE_PAREN, "Expected ')' after local class initializer")
                    self.consume(TokenType.SEMICOLON, "Expected ';' after local variable declaration")

                    return nodes.Multiple(nodes=[
                        nodes.LocalStruct(name=var_name.value, type=var_type, location=var_name.location),
                        nodes.CallFunction(name=f"__{var_type.data['class_name']}_init_", args=args, location=var_name.location)
                    ])

            var_value = self.parse_expression() if self.match(TokenType.EQUALS) else None
            self.consume(TokenType.SEMICOLON, "Expected ';' after local variable declaration")
            return nodes.LocalVariable(name=var_name.value, location=var_name.location, type=var_type, value=var_value)

        if self.match(TokenType.RETURN):
            location = self.previous().location
            value = self.parse_expression() if not self.check(TokenType.SEMICOLON) else None
            self.consume(TokenType.SEMICOLON, "Expected ';' after return statement")
            return nodes.Return(value=value, location=location)

        if self.match(TokenType.OPEN_BRACE):
            body = []

            while not self.check(TokenType.CLOSE_BRACE):
                body.append(self.parse_statement())

            self.consume(TokenType.CLOSE_BRACE, "Expected '}' after compound statement")
            return nodes.CompoundStatement(body=body)

        if self.match(TokenType.IF):
            self.consume(TokenType.OPEN_PAREN, "Expected '(' after if keyword")
            expr = self.parse_expression()
            self.consume(TokenType.CLOSE_PAREN, "Expected ')' after if expression")
            body = self.parse_statement()
            else_body = self.parse_statement() if self.match(TokenType.ELSE) else None
            return nodes.IfStatement(value=expr, body=body, else_body=else_body)

        if self.match(TokenType.WHILE):
            self.consume(TokenType.OPEN_PAREN, "Expected '(' after while keyword")
            expr = self.parse_expression()
            self.consume(TokenType.CLOSE_PAREN, "Expected ')' after while expression")
            body = self.parse_statement()
            return nodes.WhileStatement(value=expr, body=body)

        if self.match(TokenType.BREAK):
            node = nodes.BreakLoop(location=self.previous().location)
            self.consume(TokenType.SEMICOLON, "Expected ';' after break")
            return node

        if self.match(TokenType.ASM):
            value = self.consume(TokenType.STRING, "Expected string")
            self.consume(TokenType.SEMICOLON, "Expected ';' after asm")
            return nodes.InlineAssembly(value=value.value[1:-1])

        if self.match(TokenType.SWITCH):
            self.consume(TokenType.OPEN_PAREN, "Expected '(' after switch keyword")
            expr = self.parse_expression()
            self.consume(TokenType.CLOSE_PAREN, "Expected ')' after switch expression")
            self.consume(TokenType.OPEN_BRACE, "Expected switch body")

            cases = []
            default_case = None
            while not self.check(TokenType.CLOSE_BRACE):
                if self.match(TokenType.DEFAULT):
                    self.consume(TokenType.COLON, "Expected ':'")
                    default_case = []

                    while (not self.check(TokenType.CASE)) and (not self.check(TokenType.DEFAULT)) and (not self.check(TokenType.CLOSE_BRACE)):
                        default_case.append(self.parse_statement())

                elif self.match(TokenType.CASE):
                    case_value = self.consume_num_constant("Expected case expression (must be a constant number)")
                    self.consume(TokenType.COLON, "Expected ':'")
                    case_body = []

                    while (not self.check(TokenType.CASE)) and (not self.check(TokenType.DEFAULT)) and (not self.check(TokenType.CLOSE_BRACE)):
                        case_body.append(self.parse_statement())

                    cases.append((int(case_value.value), case_body))

                else:
                    self.error(self.peek().location, "Expected a case")

            self.consume(TokenType.CLOSE_BRACE, "Expected '}' after switch cases")
            return nodes.SwitchStatement(value=expr, cases=cases, default_case=default_case)

        if self.match(TokenType.PUSH):
            value = self.parse_expression()
            self.consume(TokenType.SEMICOLON, "Expected ';' after push statement")
            return nodes.Push(value=value)

        if self.match(TokenType.POP):
            name = self.previous().value
            location = self.previous().location
            variable = self.previous() if self.match(TokenType.IDENTIFIER) else None
            self.consume(TokenType.SEMICOLON, f"Expected ';' after {name} statement")
            return nodes.Pop(name=variable.value if variable is not None else None, location=location)

        if self.match(TokenType.CALL):
            func_name = self.consume(TokenType.IDENTIFIER, "Expected function name")
            args_passed = int(self.previous().value) if self.match(TokenType.NUMBER) else 0
            self.consume(TokenType.SEMICOLON, f"Expected ';' after call statement")
            return nodes.Call(name=func_name.value, location=func_name.location, args_passed=args_passed)

        expr = self.parse_expression()
        self.consume(TokenType.SEMICOLON, "Expected ';' after expression statement")
        return nodes.ExpressionStatement(value=expr)

    def parse_expression(self):
        return self.parse_assign()

    def parse_assign(self):
        left = self.parse_bitwise()

        while self.match(TokenType.EQUALS):
            equals_token = self.previous()
            if isinstance(left, nodes.Variable):
                value = self.parse_assign()
                left = nodes.AssignVariable(name=left.name, location=left.location, value=value)
            elif isinstance(left, nodes.DereferencePointer):
                value = self.parse_assign()
                left = nodes.SetAtPointer(pointer=left.pointer, offset=left.offset, value=value, location=left.location)
            elif isinstance(left, nodes.AccessStructMember):
                value = self.parse_assign()
                left = nodes.WriteStructMember(struct_pointer=left.struct_pointer, name=left.name, value=value, location=left.location)
            elif isinstance(left, nodes.Register):
                value = self.parse_assign()
                left = nodes.AssignRegister(name=left.name, value=value)
            else:
                self.error(equals_token.location, "Invalid assignment target")

        return left

    def parse_bitwise(self):
        left = self.parse_or_and()

        while self.match(TokenType.ARROW_UP, TokenType.PIPE, TokenType.AMPERSAND):
            operation = self.previous().type
            right = self.parse_or_and()
            left = nodes.BinaryOperation(operation=operation, left=left, right=right)

        return left

    def parse_or_and(self):
        left = self.parse_equals()

        while self.match(TokenType.AND, TokenType.OR, TokenType.PRECENT):
            operation = self.previous().type
            right = self.parse_equals()
            left = nodes.BinaryOperation(operation=operation, left=left, right=right)

        return left

    def parse_equals(self):
        left = self.parse_greater()

        while self.match(TokenType.DEQUALS, TokenType.NEQUALS):
            operation = self.previous().type
            right = self.parse_greater()

            if isinstance(left, nodes.Number) and isinstance(right, nodes.Number):
                left = nodes.Number(value=int(left.value == right.value) if operation == TokenType.DEQUALS else int(left.value != right.value))
            else:
                left = nodes.BinaryOperation(operation=operation, left=left, right=right)

        return left

    def parse_greater(self):
        left = self.parse_greater_equals()

        while self.match(TokenType.GREATER, TokenType.LOWER):
            operation = self.previous().type
            right = self.parse_greater_equals()

            if isinstance(left, nodes.Number) and isinstance(right, nodes.Number):
                left = nodes.Number(value=int(left.value > right.value) if operation == TokenType.GREATER else int(left.value < right.value))
            else:
                left = nodes.BinaryOperation(operation=operation, left=left, right=right)

        return left

    def parse_greater_equals(self):
        left = self.parse_term()

        while self.match(TokenType.GEQUALS, TokenType.LEQUALS):
            operation = self.previous().type
            right = self.parse_term()

            if isinstance(left, nodes.Number) and isinstance(right, nodes.Number):
                left = nodes.Number(value=int(left.value >= right.value) if operation == TokenType.GEQUALS else int(left.value <= right.value))
            else:
                left = nodes.BinaryOperation(operation=operation, left=left, right=right)

        return left

    def parse_term(self):
        left = self.parse_factor()

        while self.match(TokenType.PLUS, TokenType.MINUS):
            operation = self.previous().type
            right = self.parse_factor()

            if isinstance(left, nodes.Number) and isinstance(right, nodes.Number):
                left = nodes.Number(value=left.value + right.value if operation == TokenType.PLUS else left.value - right.value)
            else:
                left = nodes.BinaryOperation(operation=operation, left=left, right=right)

        return left

    def parse_factor(self):
        left = self.parse_call()

        while self.match(TokenType.STAR, TokenType.SLASH):
            operation = self.previous().type
            right = self.parse_call()

            if isinstance(left, nodes.Number) and isinstance(right, nodes.Number):
                left = nodes.Number(value=left.value * right.value if operation == TokenType.STAR else left.value // right.value)
            else:
                left = nodes.BinaryOperation(operation=operation, left=left, right=right)

        return left

    def parse_call(self):
        left = self.parse_primary()

        while True:
            if self.match(TokenType.OPEN_PAREN):
                location = self.previous().location

                #if not isinstance(left, nodes.Variable):
                #    self.error(location, "Invalid call target, must be a variable or function")

                args = []

                if not self.check(TokenType.CLOSE_PAREN):
                    while True:
                        args.append(self.parse_expression())
                        if not self.match(TokenType.COMMA): break

                self.consume(TokenType.CLOSE_PAREN, "Expected ')' after function call arguments")

                if isinstance(left, nodes.Variable):
                    left = nodes.CallFunction(name=left.name, location=location, args=args)
                else:
                    left = nodes.CallFunctionExpression(value=left, args=args, location=location)

            elif self.match(TokenType.OPEN_SQUARE):
                location = self.previous().location
                offset = self.parse_expression()
                self.consume(TokenType.CLOSE_SQUARE, "Expected ']' after pointer dereference offset")
                left = nodes.DereferencePointer(pointer=left, offset=offset, location=location)
                
            elif self.match(TokenType.DOT):
                field_name = self.consume(TokenType.IDENTIFIER, "Expected field name")
                left = nodes.AccessStructMember(struct_pointer=left, name=field_name.value, location=field_name.location)

            else:
                break

        return left

    def parse_primary(self):
        if self.match(TokenType.NUMBER):
            return nodes.Number(value=int(self.previous().value))

        if self.match(TokenType.CHAR):
            value = self.previous().value[1:-1]
            if value == '\\0': return nodes.Number(0)
            if value == '\\r': value = '\r'
            if value == '\\n': value = '\n'
            if value == '\\t': value = '\t'
            if value == '\\\'': value = "'"
            if value == '\\\\': value = "\\"
            return nodes.Number(value=ord(value))

        if self.match(TokenType.STRING):
            return nodes.String(value=self.previous().value, location=self.previous().location)

        if self.match(TokenType.IDENTIFIER):
            return nodes.Variable(name=self.previous().value, location=self.previous().location)

        if self.match(TokenType.OPEN_PAREN):
            if (cast_type := self.match_type()):
                self.consume(TokenType.CLOSE_PAREN, "Expected ')' after cast type")
                cast_expr = self.parse_expression()
                return nodes.Cast(type=cast_type, value=cast_expr)

            expr = self.parse_expression()
            self.consume(TokenType.CLOSE_PAREN, "Expected ')' after expression")
            return expr

        if self.match(TokenType.MINUS):
            expr = self.parse_call()
            return nodes.BinaryOperation(left=nodes.Number(value=0), right=expr, operation=TokenType.MINUS)

        if self.match(TokenType.AND):
            name = self.consume(TokenType.IDENTIFIER, "Expected variable name")
            return nodes.AddressOf(name=name.value, location=name.location)

        if self.match(TokenType.STAR):
            location = self.previous().location
            value = self.parse_bitwise()
            return nodes.DereferencePointer(pointer=value, offset=nodes.Number(0), location=location)

        if self.match(TokenType.BANG):
            value = self.parse_bitwise()
            return nodes.Negate(value=value)

        if self.match(TokenType.STAR):
            location = self.previous().location
            value = self.parse_bitwise()
            return nodes.DereferencePointer(pointer=value, offset=nodes.Number(value=0), location=location)

        if self.match(TokenType.TRUE): return nodes.Number(value=1)
        if self.match(TokenType.FALSE): return nodes.Number(value=0)

        if self.match(TokenType.RES):
            location = self.previous().location
            res_type = self.consume_type("Expected reserve type")

            if self.match(TokenType.OPEN_SQUARE):
                values = []

                if not self.check(TokenType.CLOSE_SQUARE):
                    while True:
                        values.append(self.parse_constant())
                        if not self.match(TokenType.COMMA): break

                self.consume(TokenType.CLOSE_SQUARE, "Expected ']' after reserve initial values")
                return nodes.ReserveInitialized(type=res_type, data=values, location=location)

            res_size = self.consume(TokenType.NUMBER, "Expected reserve count")
            return nodes.ReserveUninitialized(type=res_type, size=int(res_size.value), location=location)

        if self.match(TokenType.AMPERSAND):
            name = self.consume(TokenType.IDENTIFIER, "Expected variable name")
            return nodes.AddressOf(name=name.value, location=name.location)

        if self.match(TokenType.SIZEOF):
            self.consume(TokenType.OPEN_PAREN, "Expected '(' after sizeof keyword")

            if (stype := self.match_type()):
                self.consume(TokenType.CLOSE_PAREN, "Expected ')' after sizeof type")
                return nodes.SizeofType(type=stype)
                
            value = self.parse_expression()
            self.consume(TokenType.CLOSE_PAREN, "Expected ')' after sizeof value")
            return nodes.Sizeof(value=value)

        if self.match(TokenType.NEW):
            name = self.consume(TokenType.IDENTIFIER, "Expected class name")
            args = []

            if self.match(TokenType.OPEN_PAREN):
                if not self.check(TokenType.CLOSE_PAREN):
                    while True:
                        args.append(self.parse_expression())
                        if not self.match(TokenType.COMMA): break

                self.consume(TokenType.CLOSE_PAREN, "Expected ')' after initializer arguments")

            return nodes.NewInstance(name=name.value, args=args, location=name.location)

        if self.match(TokenType.REGISTER):
            return nodes.Register(name=self.previous().value[1:])

        self.error(self.peek().location, "Expected expression")

    def consume_num_constant(self, error_msg):
        if self.match(TokenType.NUMBER):
            return nodes.Number(value=int(self.previous().value))

        if self.match(TokenType.CHAR):
            value = self.previous().value[1:-1]
            if value == '\\0': return nodes.Number(0)
            if value == '\\r': value = '\r'
            if value == '\\n': value = '\n'
            if value == '\\t': value = '\t'
            if value == '\\\'': value = "'"
            if value == '\\\\': value = "\\"
            return nodes.Number(value=ord(value))

        if self.match(TokenType.IDENTIFIER):
            enum_name = self.previous()
            if self.match(TokenType.DOT):
                field = self.consume(TokenType.IDENTIFIER, "Expected field name after '.'")

                if enum_name.value in self.enum_data:
                    return nodes.Number(value=self.enum_data[enum_name.value][field.value])


        self.error(self.peek().location, error_msg)

    def parse_constant(self):
        if self.match(TokenType.NUMBER):
            return nodes.Number(value=int(self.previous().value))

        if self.match(TokenType.STRING):
            return nodes.String(value=self.previous().value, location=self.previous().location)

        if self.match(TokenType.CHAR):
            value = self.previous().value[1:-1]
            if value == '\\0': return nodes.Number(0)
            if value == '\\r': value = '\r'
            if value == '\\n': value = '\n'
            if value == '\\t': value = '\t'
            if value == '\\\'': value = "'"
            if value == '\\\\': value = "\\"
            return nodes.Number(value=ord(value))

        if self.match(TokenType.TRUE): return nodes.Number(value=1)
        if self.match(TokenType.FALSE): return nodes.Number(value=0)

        if self.match(TokenType.RES):
            location = self.previous().location
            res_type = self.consume_type("Expected reserve type")

            if self.match(TokenType.OPEN_SQUARE):
                values = []

                if not self.check(TokenType.CLOSE_SQUARE):
                    while True:
                        values.append(self.parse_constant())
                        if not self.match(TokenType.COMMA): break

                self.consume(TokenType.CLOSE_SQUARE, "Expected ']' after reserve initial values")
                return nodes.ReserveInitialized(type=res_type, data=values, location=location)

            res_size = self.consume(TokenType.NUMBER, "Expected reserve count")
            return nodes.ReserveUninitialized(type=res_type, size=int(res_size.value), location=location)

        self.error(self.peek().location, "Expected constant expression")

    # helper functions

    def match_type(self):
        if not self.match(TokenType.U8, TokenType.U16, TokenType.U32, TokenType.U64, TokenType.I8, TokenType.I16, TokenType.I32, TokenType.I64, TokenType.PTR):
            prev = self.peek()

            if self.match(TokenType.STRUCT):
                sub_struct_fields = self.parse_sub_struct()
                return nodes.Type(id=nodes.TypeEnum.SUB_STRUCT, data={'fields': sub_struct_fields})

            if not prev.value in self.typedefs:
                return

            final_type = self.typedefs[prev.value]
            self.advance()

            while self.match(TokenType.STAR):
                final_type = nodes.Type(id=nodes.TypeEnum.PTR, is_base_type=False, base_type=final_type)

            return final_type
        
        type_id = TOKEN_VAR_TYPE[self.previous().type]
        final_type = nodes.Type(id=type_id)

        while self.match(TokenType.STAR):
            final_type = nodes.Type(id=nodes.TypeEnum.PTR, is_base_type=False, base_type=final_type)

        return final_type

    def consume_type(self, error_msg = None):
        if (final_type := self.match_type()):
            return final_type

        self.error(self.peek().location, error_msg or "Expected type")

    def match(self, *types) -> bool:
        for token_type in types:
            if self.peek().type == token_type:
                self.advance()
                return True

        return False

    def check(self, type_) -> bool:
        return self.peek().type == type_

    def consume(self, expected_type: str, error_msg: str) -> Token:
        if self.peek().type == expected_type: return self.advance()

        self.error(self.peek().location, error_msg)

    def previous(self) -> Token:
        return self.tokens[self.pos - 1]

    def advance(self) -> Token:
        token = self.peek()
        self.pos += 1
        return token

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def available(self) -> bool:
        return self.peek().type != TokenType.EOF

    def error(self, location, error_msg):
        raise ParserError(error_msg, location)


class ParserError(Exception):
    def __init__(self, msg, location: TokenLocation) -> None:
        self.msg = msg
        self.location = location

    def __repr__(self) -> str:
        return "%s:%d:%d: [ERROR]: %s" % (self.location + (self.msg,))

    def __str__(self) -> str:
        return "%s:%d:%d: [ERROR]: %s" % (self.location + (self.msg,))