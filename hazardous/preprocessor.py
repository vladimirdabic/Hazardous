from typing import List, final
from .scanner import Token, TokenType, TokenLocation, Scanner


class Preprocessor:
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

    def advance(self) -> Token:
        token = self.peek()
        self.pos += 1
        return token

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def available(self) -> bool:
        return self.peek().type != TokenType.EOF

    def error(self, location, error_msg):
        raise PreprocessorError(error_msg, location)


    def preprocess(self, tokens: List[Token], include_dirs: list, setup = True):
        self.tokens = tokens
        self.pos = 0
        if setup:
            self.macros = {}
            self.included = []
        new_tokens = []

        while self.available():
            token = self.advance()

            if token.type == TokenType.DEFINE:
                name = self.consume(TokenType.IDENTIFIER, "Expected macro name")
                macro_args = []

                if self.match(TokenType.OPEN_PAREN):
                    while True:
                        macro_args.append(self.consume(TokenType.IDENTIFIER, "Expected macro argument").value)
                        if not self.match(TokenType.COMMA): break
                    self.consume(TokenType.CLOSE_PAREN, "Expected ')' for macro")

                macro_tokens = []
                if self.match(TokenType.OPEN_SQUARE):
                    while not self.check(TokenType.CLOSE_SQUARE):
                        if self.available():
                            macro_tokens.append(self.advance())
                        else:
                            self.error(name.location, "Expected ']' after macro definition")

                    self.consume(TokenType.CLOSE_SQUARE, "Expected ']' after macro definition")

                else:
                    if not self.available():
                        raise PreprocessorError("Expected macro value", name.location)

                    macro_tokens.append(self.advance())


                if len(macro_tokens) == 0:
                    raise PreprocessorError("Wtf?", token.location)

                preprocessor = Preprocessor()
                preprocessor.macros = self.macros
                preprocessor.included = self.included
                macro_tokens.append(Token(type=TokenType.EOF, value=None, location=macro_tokens[-1].location))
                
                preprocessed = preprocessor.preprocess(macro_tokens, include_dirs, setup=False)

                self.macros[name.value] = {
                    "tokens": preprocessed[:-1],
                    "args": macro_args
                }

            elif token.type == TokenType.INCLUDE:
                file = self.consume(TokenType.STRING, "Expected file name")
                scanner = Scanner()
                preprocessor = Preprocessor()
                preprocessor.macros = self.macros
                preprocessor.included = self.included
                file_name = file.value[1:-1]
                code = None

                if file_name not in self.included:
                    for path in include_dirs:
                        try:
                            f = open(path + file_name, "r")
                            code = f.read()
                            f.close()
                        except FileNotFoundError:
                            pass

                    if not code:
                        self.error(token.location, f"File '{file_name}' not found")

                    self.included.append(file_name)

                    scanner.input(code, file_name)
                    preprocessed = preprocessor.preprocess(list(scanner.tokens()), include_dirs, setup=False)
                    new_tokens.extend(preprocessed[:-1])

            elif token.type == TokenType.IDENTIFIER:
                expanded = self.expand_token(token)
                new_tokens.extend(expanded)

            else:
                new_tokens.append(token)

        new_tokens.append(tokens[-1])
        return new_tokens

    def expand_token(self, token: Token):
        if token.value in self.macros:
            if len(self.macros[token.value]['args']) > 0:
                args = []
                cur_arg = None
                arg_id = 0
                macro_tokens = self.macros[token.value]['tokens']

                if self.match(TokenType.OPEN_PAREN):
                    opens = 1
                    if not self.check(TokenType.CLOSE_PAREN):
                        while True:
                            cur_arg = []
                            while not self.check(TokenType.COMMA) and self.available() and opens > 0:
                                tok = self.advance()
                                if tok.type == TokenType.OPEN_PAREN: opens += 1
                                if tok.type == TokenType.CLOSE_PAREN: opens -= 1
                                if opens == 0: break
                                if tok.type == TokenType.IDENTIFIER:
                                    expanded = self.expand_token(tok)
                                    cur_arg.extend(expanded)
                                else:
                                    cur_arg.append(tok)
                            args.append(cur_arg)
                            arg_id += 1
                            if arg_id >= len(macro_tokens):
                                self.error(token.location, "Too many arguments passed to macro")

                            if not self.match(TokenType.COMMA): break

                    if opens > 0:
                        self.error(token.location, "Unclosed macro arguments")
                    #self.consume(TokenType.CLOSE_PAREN, "Expected ')' for macro")

                final_tokens = []

                for macro_token in macro_tokens:
                    if macro_token.type == TokenType.IDENTIFIER and macro_token.value in self.macros[token.value]['args']:
                        idx = self.macros[token.value]['args'].index(macro_token.value)
                        final_tokens.extend(args[idx])
                        #print(args[idx])
                    else:
                        #print(macro_token)
                        final_tokens.append(macro_token)

                #print(final_tokens)
                return final_tokens
            else:
                return self.macros[token.value]['tokens']
        else:
            return [token]


class PreprocessorError(Exception):
    def __init__(self, msg, location: TokenLocation) -> None:
        self.msg = msg
        self.location = location

    def __repr__(self) -> str:
        return "%s:%d:%d: [ERROR]: %s" % (self.location + (self.msg,))

    def __str__(self) -> str:
        return "%s:%d:%d: [ERROR]: %s" % (self.location + (self.msg,))