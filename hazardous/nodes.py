from dataclasses import dataclass
from typing import List, Tuple
from .scanner import Token, TokenLocation, TokenType
from enum import IntEnum, auto


class TypeEnum(IntEnum):
    U8 = auto()
    U16 = auto()
    U32 = auto()
    U64 = auto()
    I8 = auto()
    I16 = auto()
    I32 = auto()
    I64 = auto()
    PTR = auto()
    PROCPTR = auto()
    STRUCT = auto()
    SUB_STRUCT = auto()
    CLASS = auto()
    ENUM = auto()
    ARRAY = auto()
    NONE = auto()


@dataclass
class Type:
    id: TypeEnum
    is_base_type: bool = True
    base_type: any = None
    data: dict = None


@dataclass
class ProgramVariable:
    name: str
    type: Type
    is_local: bool
    location: TokenLocation


@dataclass
class ProgramProcedure:
    name: str
    return_type: Type
    body: list
    args: List[Tuple[Type, str]]
    location: TokenLocation
    forward_declared: bool
    varargs: bool
    stdcall: bool
    is_local: bool
    always: bool = False


@dataclass
class ProgramExternProcedure:
    name: str
    return_type: Type
    args: List[Tuple[Type, str]]
    varargs: bool
    stdcall: bool
    location: TokenLocation


@dataclass
class ProgramExternVariable:
    name: str
    type: Type
    location: TokenLocation


@dataclass
class LocalVariable:
    name: str
    type: Type
    value: any
    location: TokenLocation


@dataclass
class LocalStruct:
    name: str
    type: Type
    location: TokenLocation


@dataclass
class LocalArray:
    name: str
    type: Type
    size: int
    location: TokenLocation


@dataclass
class Variable:
    name: str
    location: TokenLocation


@dataclass
class AssignVariable:
    name: str
    value: any
    location: TokenLocation


@dataclass
class Number:
    value: int


@dataclass
class String:
    value: str
    location: TokenLocation


@dataclass
class BinaryOperation:
    left: any
    right: any
    operation: TokenType


@dataclass
class CallFunction:
    name: str
    args: list
    location: TokenLocation


@dataclass
class CallFunctionExpression:
    value: any
    args: list
    location: TokenLocation


@dataclass
class Cast:
    type: Type
    value: any


@dataclass
class ExpressionStatement:
    value: any


@dataclass
class Return:
    value: any
    location: TokenLocation


@dataclass
class DereferencePointer:
    pointer: any
    offset: any
    location: TokenLocation


@dataclass
class SetAtPointer:
    pointer: any
    offset: any
    value: any
    location: TokenLocation


@dataclass
class ReserveUninitialized:
    type: Type
    size: int
    location: TokenLocation


@dataclass
class ReserveInitialized:
    type: Type
    data: list
    location: TokenLocation


@dataclass
class AddressOf:
    name: str
    location: TokenLocation

@dataclass
class ProgramStruct:
    name: str
    members: List[Tuple[Type, str]]
    location: TokenLocation


@dataclass
class ProgramClass:
    name: str
    members: list
    methods: dict
    initializer: dict
    location: TokenLocation


@dataclass
class AccessStructMember:
    struct_pointer: any
    name: str
    location: TokenLocation


@dataclass
class WriteStructMember:
    struct_pointer: any
    name: str
    value: any
    location: TokenLocation


@dataclass
class Sizeof:
    value: any


@dataclass
class SizeofType:
    type: Type


@dataclass
class Negate:
    value: any


@dataclass
class IfStatement:
    value: any
    body: any
    else_body: any


@dataclass
class WhileStatement:
    value: any
    body: any
    
    
@dataclass
class CompoundStatement:
    body: list


@dataclass
class BreakLoop:
    location: TokenLocation


@dataclass
class NewInstance:
    name: str
    args: list
    location: TokenLocation


@dataclass
class Register:
    name: str


@dataclass
class AssignRegister:
    name: str
    value: any


@dataclass
class Multiple:
    nodes: list


@dataclass
class SwitchStatement:
    value: any
    cases: List[Tuple[int, list]]
    default_case: list


@dataclass
class Enumeration:
    name: str
    values: dict


@dataclass
class Push:
    value: any


@dataclass
class Pop:
    name: str
    location: TokenLocation


@dataclass
class Call:
    name: str
    location: TokenLocation
    args_passed: int = 0


@dataclass
class InlineAssembly:
    value: str