from typing import Dict, List, Optional
from enum import Enum

class SymbolKind(Enum):
    VARIABLE = "variable"
    FUNCTION = "function"
    PARAMETER = "parameter"
    STRUCT = "struct"

class Symbol:
    def __init__(self, name: str, kind: SymbolKind, type_name: str, line: int, column: int,
                 params: Optional[List['Symbol']] = None, return_type: Optional[str] = None,
                 is_external: bool = False, is_variadic: bool = False,
                 array_size: int = 0):          # новое поле
        self.name = name
        self.kind = kind
        self.type_name = type_name   # для массива – тип элемента
        self.line = line
        self.column = column
        self.params = params or []
        self.return_type = return_type
        self.fields: Dict[str, 'Symbol'] = {}
        self.is_external = is_external
        self.is_variadic = is_variadic
        self.array_size = array_size   # 0 = не массив, иначе размер

class SymbolTable:
    def __init__(self):
        self.scopes: List[Dict[str, Symbol]] = [{}]   # все области, индекс 0 - глобальная
        self.current_scope = 0

    def enter_scope(self):
        """Создать новую вложенную область."""
        self.scopes.append({})
        self.current_scope += 1

    def exit_scope(self):
        """Выйти из текущей области (не удаляя её из списка)."""
        if self.current_scope > 0:
            self.current_scope -= 1

    def insert(self, name: str, symbol: Symbol) -> bool:
        """Вставить символ в текущую область. Вернуть False, если уже существует."""
        if name in self.scopes[self.current_scope]:
            return False
        self.scopes[self.current_scope][name] = symbol
        return True

    def lookup(self, name: str) -> Optional[Symbol]:
        """Поиск от текущей области к глобальной."""
        for i in range(self.current_scope, -1, -1):
            if name in self.scopes[i]:
                return self.scopes[i][name]
        return None

    def lookup_local(self, name: str) -> Optional[Symbol]:
        """Поиск только в текущей области."""
        if name in self.scopes[self.current_scope]:
            return self.scopes[self.current_scope][name]
        return None

    def dump(self) -> str:
        """Выводит все области (включая завершённые) для отладки."""
        lines = []
        for i, scope in enumerate(self.scopes):
            if scope:  # только непустые
                lines.append(f"Scope {i}:")
                for name, sym in scope.items():
                    lines.append(f"  {name} ({sym.kind.value}) : {sym.type_name}")
        return "\n".join(lines) if lines else "(empty symbol table)"