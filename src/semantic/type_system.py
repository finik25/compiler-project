from src.lexer.token import TokenType

def is_compatible(expected: str, actual: str) -> bool:
    if expected == actual:
        return True
    # строковый литерал совместим с char*
    if expected == "char*" and actual == "string":
        return True
    # Указатели: один уровень косвенности
    if expected.endswith("*") and actual.endswith("*"):
        # Для простоты считаем совместимыми любые указатели (пока)
        return True
    # Разрешаем присваивание адреса (указатель) целому числу (для демо)
    if expected == "int" and actual.endswith("*"):
        return True
    # Разрешаем присваивание целого числа указателю (для демо)
    if expected.endswith("*") and actual == "int":
        return True
    # int -> unsigned int
    if expected == "unsigned int" and actual == "int":
        return True
    # int -> float
    if expected == "float" and actual == "int":
        return True
    return False

def get_binary_result_type(op: TokenType, left_type: str, right_type: str) -> str:
    """Возвращает тип результата бинарной операции или None, если типы не совместимы."""
    # Сравнение указателя с нулём (0) – должно быть самым приоритетным
    if op in (TokenType.EQ, TokenType.NE):
        if (left_type.endswith("*") and right_type == "int") or (left_type == "int" and right_type.endswith("*")):
            return "bool"
    # Обработка unsigned int и смешанных с int
    if left_type == "unsigned int" or right_type == "unsigned int":
        # Арифметические операторы
        if op in (TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            # Если один из операндов float – ошибка (несовместимо)
            if left_type == "float" or right_type == "float":
                return None
            return "unsigned int"
        # Операторы сравнения
        if op in (TokenType.LT, TokenType.LE, TokenType.GT, TokenType.GE, TokenType.EQ, TokenType.NE):
            if left_type == "float" or right_type == "float":
                return None
            return "bool"
        # Логические операторы – только для bool
        if op in (TokenType.AND, TokenType.OR):
            return None

    # Обработка обычных типов (int, float)
    if op in (TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
        if left_type == "int" and right_type == "int":
            return "int"
        if left_type == "float" and right_type == "float":
            return "float"
        if (left_type == "int" and right_type == "float") or (left_type == "float" and right_type == "int"):
            return "float"
        return None

    if op in (TokenType.LT, TokenType.LE, TokenType.GT, TokenType.GE, TokenType.EQ, TokenType.NE):
        if left_type == right_type or (left_type in ("int","float") and right_type in ("int","float")):
            return "bool"
        return None

    if op in (TokenType.AND, TokenType.OR):
        if left_type == "bool" and right_type == "bool":
            return "bool"
        return None

    return None

def get_unary_result_type(op: TokenType, operand_type: str) -> str:
    # Унарный минус и логическое НЕ
    if op == TokenType.MINUS:
        if operand_type in ("int", "float"):
            return operand_type
        return None
    if op == TokenType.NOT:
        if operand_type == "bool":
            return "bool"
        return None
    # Инкремент/декремент
    if op in (TokenType.INC_OP, TokenType.DEC_OP):
        if operand_type in ("int", "float", "unsigned int"):
            return operand_type
        return None
    # Оператор & (взятие адреса)
    if op == TokenType.AMP:
        # &var -> тип указателя
        return operand_type + "*"
    # Оператор * (разыменование)
    if op == TokenType.STAR:
        # *ptr -> удаляем последнюю *
        if operand_type.endswith("*"):
            return operand_type[:-1]
        return None
    return None

def size_of(type_name: str) -> int:
    """Возвращает размер в байтах для базовых типов (для массивов не используется, т.к. размер хранится отдельно)."""
    if type_name in ("int", "unsigned int", "bool"):
        return 4   # 32-bit
    elif type_name == "float":
        return 8   # double precision
    elif type_name.endswith("*"):
        return 8   # указатель 64-bit
    elif type_name == "void":
        return 0
    else:
        # Для структур нужно будет считать сумму полей, пока вернём 0
        return 0