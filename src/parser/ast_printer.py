from src.parser.ast import *


class ASTPrinter:
    """Pretty printer for AST nodes."""

    def __init__(self, verbose=False):
        self.verbose = verbose

    def print_text(self, node: ASTNode, indent: int = 0) -> str:
        """Return a text representation of the AST."""
        result = []
        indent_str = "  " * indent

        if isinstance(node, ProgramNode):
            result.append(f"{indent_str}Program:")
            for decl in node.declarations:
                result.append(self.print_text(decl, indent + 1))

        elif isinstance(node, FunctionDeclNode):
            result.append(f"{indent_str}FunctionDecl: {node.name} -> {node.return_type}")
            if node.parameters:
                result.append(f"{indent_str}  Parameters:")
                for p in node.parameters:
                    result.append(f"{indent_str}    {p.type_name} {p.name}")
            if node.body:
                result.append(f"{indent_str}  Body:")
                result.append(self.print_text(node.body, indent + 2))

        elif isinstance(node, StructDeclNode):
            result.append(f"{indent_str}StructDecl: {node.name}")
            if node.fields:
                result.append(f"{indent_str}  Fields:")
                for field in node.fields:
                    result.append(self.print_text(field, indent + 2))

        elif isinstance(node, VarDeclNode):
            if node.initializer:
                init = self.print_text(node.initializer, 0)
                result.append(f"{indent_str}VarDecl: {node.type_name} {node.name} = {init}")
            else:
                result.append(f"{indent_str}VarDecl: {node.type_name} {node.name}")

        elif isinstance(node, BlockStmtNode):
            result.append(f"{indent_str}Block:")
            for stmt in node.statements:
                result.append(self.print_text(stmt, indent + 1))

        elif isinstance(node, ExprStmtNode):
            result.append(f"{indent_str}ExprStmt:")
            result.append(self.print_text(node.expression, indent + 1))

        elif isinstance(node, IfStmtNode):
            result.append(f"{indent_str}IfStmt:")
            result.append(f"{indent_str}  Condition:")
            result.append(self.print_text(node.condition, indent + 2))
            result.append(f"{indent_str}  Then:")
            result.append(self.print_text(node.then_branch, indent + 2))
            if node.else_branch:
                result.append(f"{indent_str}  Else:")
                result.append(self.print_text(node.else_branch, indent + 2))

        elif isinstance(node, WhileStmtNode):
            result.append(f"{indent_str}WhileStmt:")
            result.append(f"{indent_str}  Condition:")
            result.append(self.print_text(node.condition, indent + 2))
            result.append(f"{indent_str}  Body:")
            result.append(self.print_text(node.body, indent + 2))

        elif isinstance(node, ForStmtNode):
            result.append(f"{indent_str}ForStmt:")
            if node.init:
                result.append(f"{indent_str}  Init:")
                result.append(self.print_text(node.init, indent + 2))
            if node.condition:
                result.append(f"{indent_str}  Condition:")
                result.append(self.print_text(node.condition, indent + 2))
            if node.update:
                result.append(f"{indent_str}  Update:")
                result.append(self.print_text(node.update, indent + 2))
            if node.body:
                result.append(f"{indent_str}  Body:")
                result.append(self.print_text(node.body, indent + 2))

        elif isinstance(node, ReturnStmtNode):
            if node.value:
                result.append(f"{indent_str}Return: {self.print_text(node.value, 0)}")
            else:
                result.append(f"{indent_str}Return")

        elif isinstance(node, EmptyStmtNode):
            result.append(f"{indent_str}EmptyStmt")

        elif isinstance(node, LiteralExprNode):
            result.append(f"{indent_str}{repr(node.value)}")

        elif isinstance(node, IdentifierExprNode):
            result.append(f"{indent_str}{node.name}")

        elif isinstance(node, BinaryExprNode):
            left = self.print_text(node.left, 0)
            right = self.print_text(node.right, 0)
            result.append(f"{indent_str}({left} {node.operator.name} {right})")

        elif isinstance(node, UnaryExprNode):
            result.append(f"{indent_str}({node.operator.name} {self.print_text(node.operand, 0)})")

        elif isinstance(node, PostfixExprNode):
            result.append(f"{indent_str}({self.print_text(node.operand, 0)}{node.operator.name})")

        elif isinstance(node, CallExprNode):
            args = ", ".join(self.print_text(a, 0) for a in node.arguments)
            result.append(f"{indent_str}{node.callee}({args})")

        elif isinstance(node, AssignmentExprNode):
            result.append(f"{indent_str}({node.target} {node.operator.name} {self.print_text(node.value, 0)})")

        else:
            result.append(f"{indent_str}<unknown node {type(node).__name__}>")

        return "\n".join(result)