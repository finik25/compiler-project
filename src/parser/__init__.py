"""Parser module for MiniCompiler."""

from src.parser.ast import (
    ASTNode,
    ProgramNode,
    FunctionDeclNode,
    StructDeclNode,
    VarDeclNode,
    ParamNode,
    BlockStmtNode,
    ExprStmtNode,
    IfStmtNode,
    WhileStmtNode,
    ForStmtNode,
    ReturnStmtNode,
    EmptyStmtNode,
    ExpressionNode,
    LiteralExprNode,
    IdentifierExprNode,
    BinaryExprNode,
    UnaryExprNode,
    PostfixExprNode,
    CallExprNode,
    AssignmentExprNode,
    NodeType,
)

from src.parser.parser import Parser, ParseError
from src.parser.ast_json import ASTJSONGenerator
from .ast import ArrayAccessExprNode

__all__ = [
    # AST nodes
    "ASTNode",
    "ProgramNode",
    "FunctionDeclNode",
    "StructDeclNode",
    "VarDeclNode",
    "ParamNode",
    "BlockStmtNode",
    "ExprStmtNode",
    "IfStmtNode",
    "WhileStmtNode",
    "ForStmtNode",
    "ReturnStmtNode",
    "EmptyStmtNode",
    "ExpressionNode",
    "LiteralExprNode",
    "IdentifierExprNode",
    "BinaryExprNode",
    "UnaryExprNode",
    "PostfixExprNode",
    "CallExprNode",
    "AssignmentExprNode",
    "NodeType",
    # Parser
    "Parser",
    "ParseError",
]