import re
from enum import IntEnum, auto
from dataclasses import dataclass
from typing import Iterator, Tuple


class TokenType(IntEnum):
    NUMBER = auto()
    STRING = auto()
    IDENTIFIER = auto()
    CHAR = auto()

    OPEN_PAREN = auto()
    CLOSE_PAREN = auto()
    OPEN_SQUARE = auto()
    CLOSE_SQUARE = auto()
    OPEN_BRACE = auto()
    CLOSE_BRACE = auto()

    SEMICOLON = auto()
    COLON = auto()
    QUESTION_MARK = auto()
    DOT = auto()
    COMMA = auto()
    
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    BANG = auto()
    SLASH = auto()
    PIPE = auto()
    EQUALS = auto()
    PRECENT = auto()
    ARROW_UP = auto()
    AMPERSAND = auto()
    POINTER_ARROW = auto()

    VARARGS = auto()
    
    AND = auto()
    OR = auto()
    DEQUALS = auto()
    NEQUALS = auto()
    GREATER = auto()
    GEQUALS = auto()
    LOWER = auto()
    LEQUALS = auto()
    
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    BREAK = auto()
    EXTERNAL = auto()
    RETURN = auto()
    LOCAL = auto()
    TRUE = auto()
    FALSE = auto()
    NEW = auto()
    VAR = auto()
    STDCALL = auto()
    RES = auto()
    SIZEOF = auto()
    SWITCH = auto()
    CASE = auto()
    DEFAULT = auto()
    PUSH = auto()
    POP = auto()
    CALL = auto()
    ASM = auto()

    PROC = auto()
    PTR = auto()
    U8 = auto()
    U16 = auto()
    U32 = auto()
    U64 = auto()
    I8 = auto()
    I16 = auto()
    I32 = auto()
    I64 = auto()
    STRUCT = auto()
    ENUM = auto()
    CLASS = auto()

    DEFINE = auto()
    INCLUDE = auto()

    REGISTER = auto()

    EOF = auto()

TokenLocation = Tuple[str, int, int]

@dataclass
class Token:
    type: TokenType
    value: any
    location: TokenLocation


class ScannerError(Exception):
    def __init__(self, msg, location: TokenLocation) -> None:
        self.msg = msg
        self.location = location

    def __repr__(self) -> str:
        return "%s:%d:%d: [ERROR]: %s" % (self.location + (self.msg,))

    def __str__(self) -> str:
        return "%s:%d:%d: [ERROR]: %s" % (self.location + (self.msg,))


class Scanner:
    ws_skip = re.compile(r'[^\t\r ]')

    token_definitions = {
        'NEWLINE':                     r'\n',
        'IGNORE':                      r'\/\/.*',
        TokenType.NUMBER:              r'\d+',

        TokenType.STAR:                r'\*',
        TokenType.PLUS:                r'\+',
        TokenType.POINTER_ARROW:       r'->',
        TokenType.MINUS:               r'-',
        TokenType.SLASH:               r'\/',
        TokenType.OPEN_PAREN:          r'\(',
        TokenType.CLOSE_PAREN:         r'\)',
        TokenType.OPEN_SQUARE:         r'\[',
        TokenType.CLOSE_SQUARE:        r'\]',
        TokenType.OPEN_BRACE:          r'{',
        TokenType.CLOSE_BRACE:         r'}',
        TokenType.COMMA:               r',',
        TokenType.VARARGS:             r'\.\.\.',
        TokenType.DOT:                 r'\.',
        TokenType.SEMICOLON:           r';',
        TokenType.COLON:               r':',
        TokenType.OR:                  r'\|\||\bor\b',
        TokenType.AND:                 r'&&|\band\b',
        TokenType.ARROW_UP:            r'\^',
        TokenType.PIPE:                r'\|',
        TokenType.AMPERSAND:           r'&',
        TokenType.NEQUALS:             r'!=',
        TokenType.BANG:                r'!',
        TokenType.QUESTION_MARK:       r'\?',
        TokenType.DEQUALS:             r'==',
        TokenType.EQUALS:              r'=',
        TokenType.GEQUALS:             r'>=',
        TokenType.GREATER:             r'>',
        TokenType.LEQUALS:             r'<=',
        TokenType.LOWER:               r'<',

        TokenType.U8:                  r'\bu8\b',
        TokenType.U16:                 r'\bu16\b',
        TokenType.U32:                 r'\bu32\b',
        TokenType.U64:                 r'\bu64\b',
        TokenType.I8:                  r'\bi8\b',
        TokenType.I16:                 r'\bi16\b',
        TokenType.I32:                 r'\bi32\b',
        TokenType.I64:                 r'\bi64\b',
        TokenType.PTR:                 r'\bptr\b',
        TokenType.PROC:                r'\bproc\b',
        TokenType.STRUCT:              r'\bstruct\b',
        TokenType.CLASS:               r'\bclass\b',
        TokenType.ENUM:                r'\benum\b',

        TokenType.LOCAL:               r'\blocal\b',
        TokenType.BREAK:               r'\bbreak\b',
        TokenType.EXTERNAL:            r'\bexternal\b',
        TokenType.RETURN:              r'\breturn\b',
        TokenType.NEW:                 r'\bnew\b',
        TokenType.TRUE:                r'\btrue\b',
        TokenType.FALSE:               r'\bfalse\b',
        TokenType.WHILE:               r'\bwhile\b',
        TokenType.IF:                  r'\bif\b',
        TokenType.ELSE:                r'\belse\b',
        TokenType.VAR:                 r'\bvar\b',
        TokenType.STDCALL:             r'\bstdcall\b',
        TokenType.RES:                 r'\bres\b',
        TokenType.SWITCH:              r'\bswitch\b',
        TokenType.CASE:                r'\bcase\b',
        TokenType.DEFAULT:             r'\bdefault\b',
        # TokenType.HERE:                r'\bhere\b',
        TokenType.PUSH:                r'\bpush\b',
        TokenType.POP:                 r'\bpop\b|\bdrop\b',
        TokenType.CALL:                r'\bcall\b',
        TokenType.ASM:                r'\basm\b',
        # TokenType.DUP:                 r'\bdup\b',
        # TokenType.SWAP:                r'\bswap\b',
        # TokenType.OVER:                r'\bover\b',
        # TokenType.RET:                 r'\bret\b',
        # TokenType.SUB:                 r'\bsub\b',
        # TokenType.MUL:                 r'\bmul\b',
        # TokenType.ADD:                 r'\badd\b',
        # TokenType.DIVMOD:              r'\bdivmod\b',
        
        # TokenType.STACK_PTR:           r'%sp\b',
        TokenType.REGISTER:            r'%rsp\b|%rbp\b|%rax\b|%rbx\b|%rcx\b|%rdx\b|%rdi\b|%rsi\b|%r8\b|%r9\b|%r10\b|%r11\b|%r12\b|%r13\b|%r14\b|%r15\b|%r16\b',
        TokenType.DEFINE:              r'%define\b',
        TokenType.INCLUDE:             r'%include\b',
        TokenType.PRECENT:             r'%',
        TokenType.SIZEOF:              r'\bsizeof\b',

        TokenType.STRING:              r'[ubf]?r?("(?!"").*?(?<!\\)(\\\\)*?")',
        TokenType.CHAR:                 r"'\\0'|'\\n'|'\\r'|'\\''|'\\t'|'\\\\'|'[ -&(-~]'",
        TokenType.IDENTIFIER:          r'[a-zA-Z_][a-zA-Z0-9_]*'
    }

    master_regex = re.compile('|'.join(
        f"(?P<G{name}>{pattern})" for name, pattern in token_definitions.items()
    ))

    def input(self, code: str, file: str) -> None:
        self.buffer = code
        self.pos = 0
        self.col = 1
        self.row = 1
        self.file = file

    def next_token(self) -> Token:
        # if position is at end, no more tokens
        if self.pos >= len(self.buffer):
            return None

        # Find first non whitespace character
        m = self.ws_skip.search(self.buffer, self.pos)

        if m:
            old_pos = self.pos
            self.pos = m.start()
            self.col += self.pos - old_pos
        else:
            # this means we didn't find a character meaning we're at the end
            return None

        # match against main regex
        m = self.master_regex.match(self.buffer, self.pos)

        if m:
            token_type = m.lastgroup

            if token_type == 'GIGNORE':
                self.pos = m.end()
                return self.next_token()

            elif token_type == 'GNEWLINE':
                self.row += 1
                self.col = 1
                self.pos = m.end()
                return self.next_token()

            string_repr = m.string[m.start():m.end()]
            token = Token(type= TokenType(int(token_type[1:])), value=string_repr, location=(self.file, self.row, self.col))

            old_pos = self.pos
            self.pos = m.end()

            self.col += self.pos - old_pos
            return token

        raise ScannerError(f"Unexpected character '{self.buffer[self.pos]}'", (self.file, self.row, self.col))

    def tokens(self) -> Iterator[Token]:
        # custom iterator
        while True:
            tok = self.next_token()
            if tok is None:
                yield Token(type=TokenType.EOF, value=None, location=(self.file, self.row, self.col))
                break
            yield tok