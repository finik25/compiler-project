from typing import Dict, List, Optional, Tuple
import re


class Preprocessor:
    """
    Preprocessor for MiniCompiler.

    Handles:
    - Comment removal (single-line // and multi-line /* */)
    - Macro definitions and expansion (#define)
    - Conditional compilation (#ifdef, #ifndef, #endif)

    Preserves line numbers for error reporting by replacing removed
    content with whitespace or newlines.
    """

    def __init__(self, source: str):
        self.original_source = source
        self.source = source
        self.macros: Dict[str, str] = {}
        self.defines: Dict[str, bool] = {}  # For #ifdef tracking
        self.include_stack: List[bool] = []  # For nested conditionals
        self.errors: List[Tuple[int, int, str]] = []  # line, column, message

    def process(self) -> str:
        """
        Process the source code through all preprocessor stages.
        Returns cleaned source code ready for lexer.
        """
        # Stage 1: Remove comments (most important for parser)
        self._remove_comments()

        # Stage 2: Process macros (optional stretch goal)
        # self._process_macros()

        # Stage 3: Handle conditionals (optional stretch goal)
        # self._process_conditionals()

        return self.source

    def _remove_comments(self):
        """
        Remove comments while preserving line numbers.

        Strategy:
        1. First, find and protect string literals
        2. Remove single-line comments (//)
        3. Remove multi-line comments (/* */)
        4. Restore string literals
        """
        # Step 1: Protect string literals
        self._protect_strings()

        # Step 2: Remove single-line comments
        self._remove_single_line_comments()

        # Step 3: Remove multi-line comments
        self._remove_multi_line_comments()

        # Step 4: Restore string literals
        self._restore_strings()

    def _protect_strings(self):
        """
        Replace string literals with placeholders to protect them
        from comment removal.
        """
        self.string_placeholders = []
        self.string_positions = []

        def replace_string(match):
            placeholder = f"__STRING_{len(self.string_placeholders)}__"
            self.string_placeholders.append(match.group(0))
            self.string_positions.append((match.start(), match.end()))
            return placeholder

        # Find all double-quoted strings
        import re
        string_pattern = r'"[^"\\]*(\\.[^"\\]*)*"'
        self.source, count = re.subn(string_pattern, replace_string, self.source)

    def _restore_strings(self):
        """Restore string literals from placeholders."""
        for i, string in enumerate(self.string_placeholders):
            placeholder = f"__STRING_{i}__"
            self.source = self.source.replace(placeholder, string)

    def _remove_single_line_comments(self):
        lines = self.source.split('\n')
        processed_lines = []

        for line in lines:
            comment_pos = line.find('//')
            if comment_pos != -1:
                # Проверяем, не внутри ли строки (упрощённо: есть ли кавычки до comment_pos)
                # Для надёжности можно использовать более сложную проверку, но пока оставим как есть
                # Удаляем всё от // до конца строки, заменяем на один пробел, если перед // был непробельный символ
                before_comment = line[:comment_pos].rstrip()
                if before_comment:
                    # Добавляем часть до комментария и один пробел (чтобы разделить токены)
                    processed_line = before_comment + ' '
                else:
                    # Строка состояла только из комментария – оставляем пустую строку
                    processed_line = ''
            else:
                processed_line = line
            processed_lines.append(processed_line)

        self.source = '\n'.join(processed_lines)

    def _remove_multi_line_comments(self):
        result = []
        i = 0
        in_comment = False
        comment_start_line = 1
        comment_start_col = 1
        line = 1
        col = 1

        while i < len(self.source):
            ch = self.source[i]

            if not in_comment and ch == '/' and i + 1 < len(self.source) and self.source[i + 1] == '*':
                # Начало комментария
                in_comment = True
                comment_start_line = line
                comment_start_col = col
                # Пропускаем '/*'
                i += 2
                # После комментария вставим один пробел позже, пока ничего не добавляем
                continue

            elif in_comment and ch == '*' and i + 1 < len(self.source) and self.source[i + 1] == '/':
                # Конец комментария
                in_comment = False
                i += 2  # пропускаем '*/'
                # Вставляем один пробел после комментария
                result.append(' ')
                if ch == '\n':  # этого не случится, т.к. ch сейчас '*', но оставим логику
                    line += 1
                    col = 1
                else:
                    col += 1
                continue

            if in_comment:
                # Внутри комментария: сохраняем переводы строк, остальное игнорируем
                if ch == '\n':
                    result.append('\n')
                    line += 1
                    col = 1
                # любой другой символ просто пропускаем (не добавляем пробел)
                i += 1
            else:
                # Вне комментария: копируем символ как есть
                result.append(ch)
                if ch == '\n':
                    line += 1
                    col = 1
                else:
                    col += 1
                i += 1

        if in_comment:
            self.errors.append((comment_start_line, comment_start_col, "Unterminated multi-line comment"))
            # Закрываем комментарий искусственно, чтобы не ломать дальнейший парсинг
            # Можно добавить пробел в конце (но ошибка уже зафиксирована)

        self.source = ''.join(result)

    def define(self, name: str, value: str = ""):
        """Define a macro."""
        self.macros[name] = value
        self.defines[name] = True

    def undefine(self, name: str):
        """Undefine a macro."""
        if name in self.macros:
            del self.macros[name]
        if name in self.defines:
            del self.defines[name]

    def get_errors(self) -> List[Tuple[int, int, str]]:
        """Return list of errors found during preprocessing."""
        return self.errors


# Simple test if run directly
if __name__ == "__main__":
    test_source = '''
    // This is a single line comment
    int x = 42; /* This is a
                    multi-line comment */
    /* Another comment */ int y = x + 10;
    // Comment at end of line

    "This is a // string /* with */ comments"
    '''

    pp = Preprocessor(test_source)
    result = pp.process()

    print("Original:")
    print(test_source)
    print("\nProcessed:")
    print(result)
    print("\nErrors:", pp.get_errors())