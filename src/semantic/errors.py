class SemanticError(Exception):
    def __init__(self, message: str, line: int, column: int, context: str = ""):
        self.message = message
        self.line = line
        self.column = column
        self.context = context
        super().__init__(f"{message} at {line}:{column}" + (f" ({context})" if context else ""))