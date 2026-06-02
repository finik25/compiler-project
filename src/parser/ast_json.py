import json
from src.parser.ast import *


class ASTJSONGenerator:
    """Генератор JSON представления AST."""

    def generate(self, node: ASTNode, indent: int = None) -> str:
        """Возвращает строку JSON с отступами (опционально)."""
        data = self._to_dict(node)
        if indent is not None:
            return json.dumps(data, indent=indent, ensure_ascii=False)
        return json.dumps(data, ensure_ascii=False)

    def _to_dict(self, node: ASTNode) -> dict:
        """Рекурсивно преобразует узел в словарь."""
        result = {
            "type": node.node_type.value,
            "line": node.line,
            "column": node.column
        }

        if isinstance(node, ProgramNode):
            result["declarations"] = [self._to_dict(d) for d in node.declarations]

        elif isinstance(node, FunctionDeclNode):
            result["name"] = node.name
            result["return_type"] = node.return_type
            result["parameters"] = [self._to_dict(p) for p in node.parameters]
            if node.body:
                result["body"] = self._to_dict(node.body)

        elif isinstance(node, StructDeclNode):
            result["name"] = node.name
            result["fields"] = [self._to_dict(f) for f in node.fields]


        elif isinstance(node, VarDeclNode):
            result["data_type"] = node.type_name
            result["name"] = node.name
            if node.initializer:
                result["initializer"] = self._to_dict(node.initializer)


        elif isinstance(node, ParamNode):
            result["data_type"] = node.type_name
            result["name"] = node.name

        elif isinstance(node, BlockStmtNode):
            result["statements"] = [self._to_dict(s) for s in node.statements]

        elif isinstance(node, ExprStmtNode):
            result["expression"] = self._to_dict(node.expression)

        elif isinstance(node, IfStmtNode):
            result["condition"] = self._to_dict(node.condition)
            result["then_branch"] = self._to_dict(node.then_branch)
            if node.else_branch:
                result["else_branch"] = self._to_dict(node.else_branch)

        elif isinstance(node, WhileStmtNode):
            result["condition"] = self._to_dict(node.condition)
            result["body"] = self._to_dict(node.body)

        elif isinstance(node, ForStmtNode):
            if node.init:
                result["init"] = self._to_dict(node.init)
            if node.condition:
                result["condition"] = self._to_dict(node.condition)
            if node.update:
                result["update"] = self._to_dict(node.update)
            if node.body:
                result["body"] = self._to_dict(node.body)

        elif isinstance(node, ReturnStmtNode):
            if node.value:
                result["value"] = self._to_dict(node.value)

        elif isinstance(node, EmptyStmtNode):
            pass  # уже достаточно type

        elif isinstance(node, LiteralExprNode):
            result["value"] = node.value
            result["literal_type"] = node.literal_type.name

        elif isinstance(node, IdentifierExprNode):
            result["name"] = node.name

        elif isinstance(node, BinaryExprNode):
            result["operator"] = node.operator.name
            result["left"] = self._to_dict(node.left)
            result["right"] = self._to_dict(node.right)

        elif isinstance(node, UnaryExprNode):
            result["operator"] = node.operator.name
            result["operand"] = self._to_dict(node.operand)

        elif isinstance(node, PostfixExprNode):
            result["operator"] = node.operator.name
            result["operand"] = self._to_dict(node.operand)

        elif isinstance(node, CallExprNode):
            result["callee"] = node.callee
            result["arguments"] = [self._to_dict(a) for a in node.arguments]


        elif isinstance(node, AssignmentExprNode):
            result["target"] = self._to_dict(node.target)  # вместо node.target как строки
            result["operator"] = node.operator.name
            result["value"] = self._to_dict(node.value)

        else:
            result["_warning"] = f"Unknown node type: {type(node).__name__}"

        return result