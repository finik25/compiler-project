from src.lexer.token import TokenType

def is_compatible(expected: str, actual: str) -> bool:
    """Проверяет, можно ли присвоить значение типа actual переменной типа expected."""
    if expected == actual:
        return True
    # Допустимые расширения: int -> float
    if expected == "float" and actual == "int":
        return True
    return False

def get_binary_result_type(op: TokenType, left_type: str, right_type: str) -> str:
    """Возвращает тип результата бинарной операции или None, если типы не совместимы."""
    # Арифметические операторы
    if op in (TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
        if left_type == "int" and right_type == "int":
            return "int"
        if left_type == "float" and right_type == "float":
            return "float"
        if left_type == "int" and right_type == "float":
            return "float"
        if left_type == "float" and right_type == "int":
            return "float"
        return None
    # Операторы сравнения
    if op in (TokenType.LT, TokenType.LE, TokenType.GT, TokenType.GE, TokenType.EQ, TokenType.NE):
        if left_type == right_type or (left_type in ("int","float") and right_type in ("int","float")):
            return "bool"
        return None
    # Логические операторы
    if op in (TokenType.AND, TokenType.OR):
        if left_type == "bool" and right_type == "bool":
            return "bool"
        return None
    return None

def get_unary_result_type(op: TokenType, operand_type: str) -> str:
    if op == TokenType.MINUS:
        if operand_type in ("int", "float"):
            return operand_type
        return None
    if op == TokenType.NOT:
        if operand_type == "bool":
            return "bool"
        return None
    if op in (TokenType.INC_OP, TokenType.DEC_OP):
        if operand_type in ("int", "float"):
            return operand_type
        return None
    return None