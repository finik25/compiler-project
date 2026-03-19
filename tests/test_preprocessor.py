import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.preprocessor.preprocessor import Preprocessor


class TestPreprocessor:

    def test_remove_single_line_comments(self):
        source = """
        int x = 42; // this is a comment
        int y = 10; // another comment
        """
        pp = Preprocessor(source)
        result = pp.process()

        # Comments should be replaced with spaces
        assert "// this is a comment" not in result
        assert "int x = 42;" in result
        assert "int y = 10;" in result

    def test_remove_multi_line_comments(self):
        source = """
        int x = 42; /* this is a 
                       multi-line
                       comment */ int y = 10;
        """
        pp = Preprocessor(source)
        result = pp.process()

        assert "/* this is a" not in result
        assert "int x = 42;" in result
        assert "int y = 10;" in result

    def test_preserve_line_numbers(self):
        source = """line1
// comment line2
line3
/* comment
   line4
   line5 */ line6"""

        pp = Preprocessor(source)
        result = pp.process()

        lines = result.split('\n')
        assert len(lines) == 6  # Should preserve 6 lines

    def test_string_literals_preserved(self):
        source = 'char* s = "This is a // comment /* inside */ string";'
        pp = Preprocessor(source)
        result = pp.process()

        # String should be unchanged
        assert '"This is a // comment /* inside */ string"' in result

    def test_unterminated_comment_error(self):
        source = "int x = 42; /* This comment never ends"
        pp = Preprocessor(source)
        result = pp.process()

        errors = pp.get_errors()
        assert len(errors) == 1
        assert "Unterminated multi-line comment" in errors[0][2]

    def test_mixed_comments(self):
        source = """
        // First comment
        int x = 42; /* Multi
                        line */ int y = 10;
        // Last comment
        """
        pp = Preprocessor(source)
        result = pp.process()

        # All comments should be gone
        assert "// First comment" not in result
        assert "/* Multi" not in result
        assert "// Last comment" not in result

        # Code should remain
        assert "int x = 42;" in result
        assert "int y = 10;" in result

    def test_comments_at_line_ends(self):
        source = """int x = 42; // end of line
int y = 10;"""
        pp = Preprocessor(source)
        result = pp.process()

        # Check that line structure is preserved
        lines = result.split('\n')
        assert len(lines) == 2
        assert "int x = 42;" in lines[0]
        assert "int y = 10;" in lines[1]

    def test_consecutive_comments(self):
        source = """// comment1
// comment2
// comment3
int x = 42;"""
        pp = Preprocessor(source)
        result = pp.process()

        lines = result.split('\n')
        assert len(lines) == 4  # Should preserve empty lines
        assert "int x = 42;" in lines[3]