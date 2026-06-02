from src.parser.ast import *


class ASTDotGenerator:
    """Генератор Graphviz DOT для визуализации AST."""

    def __init__(self):
        self.node_counter = 0

    def _next_id(self):
        self.node_counter += 1
        return f"n{self.node_counter}"

    def generate(self, node: ASTNode) -> str:
        """Возвращает строку в формате DOT."""
        self.node_counter = 0
        lines = ['digraph AST {', '  node [shape=box, fontname="Courier"];']
        root_id = self._next_id()
        self._add_node(lines, node, root_id)
        lines.append('}')
        return '\n'.join(lines)

    def _add_node(self, lines, node: ASTNode, node_id: str):
        label = self._label(node)
        lines.append(f'  {node_id} [label="{label}"];')
        for child in self._children(node):
            child_id = self._next_id()
            lines.append(f'  {node_id} -> {child_id};')
            self._add_node(lines, child, child_id)

    def _label(self, node: ASTNode) -> str:
        if isinstance(node, ProgramNode):
            return "Program"
        elif isinstance(node, FunctionDeclNode):
            return f"{node.name} : {node.return_type}"
        elif isinstance(node, StructDeclNode):
            return f"struct {node.name}"
        elif isinstance(node, VarDeclNode):
            init = " = ..." if node.initializer else ""
            return f"{node.type_name} {node.name}{init}"
        elif isinstance(node, ParamNode):
            return f"{node.type_name} {node.name}"
        elif isinstance(node, BlockStmtNode):
            return "Block"
        elif isinstance(node, ExprStmtNode):
            return "ExprStmt"
        elif isinstance(node, IfStmtNode):
            return "If"
        elif isinstance(node, WhileStmtNode):
            return "While"
        elif isinstance(node, ForStmtNode):
            return "For"
        elif isinstance(node, ReturnStmtNode):
            return "Return"
        elif isinstance(node, EmptyStmtNode):
            return ";"
        elif isinstance(node, LiteralExprNode):
            return repr(node.value)
        elif isinstance(node, IdentifierExprNode):
            return node.name
        elif isinstance(node, BinaryExprNode):
            return node.operator.name
        elif isinstance(node, UnaryExprNode):
            return node.operator.name
        elif isinstance(node, PostfixExprNode):
            return node.operator.name + " (postfix)"
        elif isinstance(node, CallExprNode):
            return f"call {node.callee}"
        elif isinstance(node, AssignmentExprNode):
            target_str = self._label(node.target)  # рекурсивно получим метку для цели
            return f"{target_str} {node.operator.name} ="
        else:
            return "?"

    def _children(self, node: ASTNode) -> list:
        children = []
        if isinstance(node, ProgramNode):
            children.extend(node.declarations)
        elif isinstance(node, FunctionDeclNode):
            children.extend(node.parameters)
            if node.body:
                children.append(node.body)
        elif isinstance(node, StructDeclNode):
            children.extend(node.fields)
        elif isinstance(node, VarDeclNode):
            if node.initializer:
                children.append(node.initializer)
        elif isinstance(node, BlockStmtNode):
            children.extend(node.statements)
        elif isinstance(node, ExprStmtNode):
            children.append(node.expression)
        elif isinstance(node, IfStmtNode):
            children.append(node.condition)
            children.append(node.then_branch)
            if node.else_branch:
                children.append(node.else_branch)
        elif isinstance(node, WhileStmtNode):
            children.append(node.condition)
            children.append(node.body)
        elif isinstance(node, ForStmtNode):
            if node.init:
                children.append(node.init)
            if node.condition:
                children.append(node.condition)
            if node.update:
                children.append(node.update)
            if node.body:
                children.append(node.body)
        elif isinstance(node, ReturnStmtNode):
            if node.value:
                children.append(node.value)
        elif isinstance(node, BinaryExprNode):
            children.append(node.left)
            children.append(node.right)
        elif isinstance(node, UnaryExprNode):
            children.append(node.operand)
        elif isinstance(node, PostfixExprNode):
            children.append(node.operand)
        elif isinstance(node, CallExprNode):
            children.extend(node.arguments)
        elif isinstance(node, AssignmentExprNode):
            children.append(node.target)
            children.append(node.value)
        return children