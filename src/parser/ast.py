from dataclasses import dataclass, field
from typing import List, Optional, Any, Union
from enum import Enum
from src.lexer.token import TokenType


class NodeType(Enum):
    """Типы узлов AST для удобства идентификации."""
    # Program
    PROGRAM = "program"

    # Declarations
    FUNCTION_DECL = "function_decl"
    STRUCT_DECL = "struct_decl"
    VAR_DECL = "var_decl"
    PARAM = "param"

    # Statements
    BLOCK = "block"
    EXPR_STMT = "expr_stmt"
    IF_STMT = "if_stmt"
    WHILE_STMT = "while_stmt"
    FOR_STMT = "for_stmt"
    RETURN_STMT = "return_stmt"
    EMPTY_STMT = "empty_stmt"

    # Expressions
    LITERAL = "literal"
    IDENTIFIER = "identifier"
    BINARY = "binary"
    UNARY = "unary"
    CALL = "call"
    ASSIGNMENT = "assignment"
    POSTFIX = "postfix"


@dataclass
class ASTNode:
    """Базовый класс для всех узлов AST."""
    node_type: NodeType
    line: int
    column: int

    def __str__(self) -> str:
        return f"{self.node_type.value} at {self.line}:{self.column}"


# ============ Program Node ============

@dataclass
class ProgramNode(ASTNode):
    """Корневой узел программы."""
    declarations: List[ASTNode] = field(default_factory=list)

    def __init__(self, declarations: List[ASTNode], line: int = 1, column: int = 1):
        super().__init__(NodeType.PROGRAM, line, column)
        self.declarations = declarations


# ============ Declaration Nodes ============

@dataclass
class ParamNode(ASTNode):
    """Параметр функции."""
    type_name: str
    name: str

    def __init__(self, type_name: str, name: str, line: int, column: int):
        super().__init__(NodeType.PARAM, line, column)
        self.type_name = type_name
        self.name = name


@dataclass
class FunctionDeclNode(ASTNode):
    """Объявление функции."""
    return_type: str
    name: str
    parameters: List[ParamNode] = field(default_factory=list)
    body: Optional['BlockStmtNode'] = None

    def __init__(self, return_type: str, name: str, parameters: List[ParamNode],
                 body: Optional['BlockStmtNode'], line: int, column: int):
        super().__init__(NodeType.FUNCTION_DECL, line, column)
        self.return_type = return_type
        self.name = name
        self.parameters = parameters
        self.body = body


@dataclass
class StructDeclNode(ASTNode):
    """Объявление структуры."""
    name: str
    fields: List['VarDeclNode'] = field(default_factory=list)

    def __init__(self, name: str, fields: List['VarDeclNode'], line: int, column: int):
        super().__init__(NodeType.STRUCT_DECL, line, column)
        self.name = name
        self.fields = fields


@dataclass
class VarDeclNode(ASTNode):
    """Объявление переменной (может использоваться как поле структуры)."""
    type_name: str
    name: str
    initializer: Optional['ExpressionNode'] = None

    def __init__(self, type_name: str, name: str, initializer: Optional['ExpressionNode'],
                 line: int, column: int):
        super().__init__(NodeType.VAR_DECL, line, column)
        self.type_name = type_name
        self.name = name
        self.initializer = initializer


# ============ Statement Nodes ============

@dataclass
class BlockStmtNode(ASTNode):
    """Блок операторов."""
    statements: List[ASTNode] = field(default_factory=list)

    def __init__(self, statements: List[ASTNode], line: int, column: int):
        super().__init__(NodeType.BLOCK, line, column)
        self.statements = statements


@dataclass
class ExprStmtNode(ASTNode):
    """Оператор-выражение."""
    expression: 'ExpressionNode'

    def __init__(self, expression: 'ExpressionNode', line: int, column: int):
        super().__init__(NodeType.EXPR_STMT, line, column)
        self.expression = expression


@dataclass
class IfStmtNode(ASTNode):
    """Условный оператор if-else."""
    condition: 'ExpressionNode'
    then_branch: ASTNode  # StatementNode
    else_branch: Optional[ASTNode] = None  # StatementNode or None

    def __init__(self, condition: 'ExpressionNode', then_branch: ASTNode,
                 else_branch: Optional[ASTNode], line: int, column: int):
        super().__init__(NodeType.IF_STMT, line, column)
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch


@dataclass
class WhileStmtNode(ASTNode):
    """Цикл while."""
    condition: 'ExpressionNode'
    body: ASTNode  # StatementNode

    def __init__(self, condition: 'ExpressionNode', body: ASTNode, line: int, column: int):
        super().__init__(NodeType.WHILE_STMT, line, column)
        self.condition = condition
        self.body = body


@dataclass
class ForStmtNode(ASTNode):
    """Цикл for."""
    init: Optional[ASTNode] = None  # VarDeclNode or ExprStmtNode
    condition: Optional['ExpressionNode'] = None
    update: Optional['ExpressionNode'] = None
    body: Optional[ASTNode] = None  # StatementNode

    def __init__(self, init: Optional[ASTNode], condition: Optional['ExpressionNode'],
                 update: Optional['ExpressionNode'], body: Optional[ASTNode],
                 line: int, column: int):
        super().__init__(NodeType.FOR_STMT, line, column)
        self.init = init
        self.condition = condition
        self.update = update
        self.body = body


@dataclass
class ReturnStmtNode(ASTNode):
    """Оператор return."""
    value: Optional['ExpressionNode'] = None

    def __init__(self, value: Optional['ExpressionNode'], line: int, column: int):
        super().__init__(NodeType.RETURN_STMT, line, column)
        self.value = value


@dataclass
class EmptyStmtNode(ASTNode):
    """Пустой оператор (один ';')."""

    def __init__(self, line: int, column: int):
        super().__init__(NodeType.EMPTY_STMT, line, column)


# ============ Expression Nodes ============

@dataclass
class ExpressionNode(ASTNode):
    """Базовый класс для всех выражений. Тип выражения будет добавлен динамически."""
    pass


@dataclass
class LiteralExprNode(ExpressionNode):
    """Литеральное значение."""
    value: Any
    literal_type: TokenType  # INT_LITERAL, FLOAT_LITERAL, STRING_LITERAL, KW_TRUE, KW_FALSE

    def __init__(self, value: Any, literal_type: TokenType, line: int, column: int):
        super().__init__(NodeType.LITERAL, line, column)
        self.value = value
        self.literal_type = literal_type


@dataclass
class IdentifierExprNode(ExpressionNode):
    """Идентификатор (переменная, функция)."""
    name: str
    symbol: Optional[Any] = None   # ссылка на Symbol из семантического анализа

    def __init__(self, name: str, line: int, column: int):
        super().__init__(NodeType.IDENTIFIER, line, column)
        self.name = name


@dataclass
class BinaryExprNode(ExpressionNode):
    """Бинарная операция."""
    left: ExpressionNode
    operator: TokenType
    right: ExpressionNode

    def __init__(self, left: ExpressionNode, operator: TokenType, right: ExpressionNode,
                 line: int, column: int):
        super().__init__(NodeType.BINARY, line, column)
        self.left = left
        self.operator = operator
        self.right = right


@dataclass
class UnaryExprNode(ExpressionNode):
    """Унарная операция (префиксная: -, !, ++, --)."""
    operator: TokenType  # MINUS, NOT, INC_OP, DEC_OP
    operand: ExpressionNode

    def __init__(self, operator: TokenType, operand: ExpressionNode, line: int, column: int):
        super().__init__(NodeType.UNARY, line, column)
        self.operator = operator
        self.operand = operand


@dataclass
class PostfixExprNode(ExpressionNode):
    """Постфиксная операция (++, --)."""
    operator: TokenType  # INC_OP, DEC_OP
    operand: ExpressionNode

    def __init__(self, operator: TokenType, operand: ExpressionNode, line: int, column: int):
        super().__init__(NodeType.POSTFIX, line, column)
        self.operator = operator
        self.operand = operand


@dataclass
class CallExprNode(ExpressionNode):
    """Вызов функции."""
    callee: str
    arguments: List[ExpressionNode] = field(default_factory=list)
    function_symbol: Optional[Any] = None   # ссылка на Symbol функции

    def __init__(self, callee: str, arguments: List[ExpressionNode], line: int, column: int):
        super().__init__(NodeType.CALL, line, column)
        self.callee = callee
        self.arguments = arguments


@dataclass
class AssignmentExprNode(ExpressionNode):
    """Оператор присваивания (используется как выражение)."""
    target: str  # имя переменной
    operator: TokenType  # ASSIGN, ADD_ASSIGN, SUB_ASSIGN, MUL_ASSIGN, DIV_ASSIGN
    value: ExpressionNode

    def __init__(self, target: str, operator: TokenType, value: ExpressionNode,
                 line: int, column: int):
        super().__init__(NodeType.ASSIGNMENT, line, column)
        self.target = target
        self.operator = operator
        self.value = value