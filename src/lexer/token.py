from enum import Enum, auto
from dataclasses import dataclass
from typing import Any, Optional

class TokenType(Enum):
    # Keywords
    KW_IF = auto()
    KW_ELSE = auto()
    KW_WHILE = auto()
    KW_FOR = auto()
    KW_INT = auto()
    KW_FLOAT = auto()
    KW_BOOL = auto()
    KW_RETURN = auto()
    KW_TRUE = auto()
    KW_FALSE = auto()
    KW_VOID = auto()
    KW_STRUCT = auto()
    KW_FN = auto()
    KW_VAR = auto()

    # Identifiers & literals
    IDENTIFIER = auto()
    INT_LITERAL = auto()
    FLOAT_LITERAL = auto()
    STRING_LITERAL = auto()

    # Operators (single-character)
    PLUS = auto()       # '+'
    MINUS = auto()      # '-'
    STAR = auto()       # '*'
    SLASH = auto()      # '/'
    PERCENT = auto()    # '%'
    ASSIGN = auto()     # '='

    # Two-character operators
    EQ = auto()         # '=='
    NE = auto()         # '!='
    LE = auto()         # '<='
    GE = auto()         # '>='
    AND = auto()        # '&&'
    OR = auto()         # '||'
    ARROW = auto()      # '->'
    INC_OP = auto()     # '++'
    DEC_OP = auto()     # '--'
    ADD_ASSIGN = auto() # '+='
    SUB_ASSIGN = auto() # '-='
    MUL_ASSIGN = auto() # '*='
    DIV_ASSIGN = auto() # '/='

    # Single-character that also appear in two-char (kept separately)
    LT = auto()         # '<'
    GT = auto()         # '>'
    NOT = auto()        # '!'

    # Delimiters
    LPAREN = auto()     # '('
    RPAREN = auto()     # ')'
    LBRACE = auto()     # '{'
    RBRACE = auto()     # '}'
    LBRACKET = auto()   # '['
    RBRACKET = auto()   # ']'
    SEMICOLON = auto()  # ';'
    COMMA = auto()      # ','
    COLON = auto()      # ':'

    # Special
    END_OF_FILE = auto()
    ERROR = auto()


@dataclass
class Token:
    type: TokenType
    lexeme: str
    line: int
    column: int
    literal: Optional[Any] = None

    def __str__(self):
        if self.literal is not None:
            return f'{self.line}:{self.column} {self.type.name} "{self.lexeme}" {self.literal!r}'
        else:
            return f'{self.line}:{self.column} {self.type.name} "{self.lexeme}"'