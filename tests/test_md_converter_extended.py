
import unittest
import os
import shutil
import tempfile
from unittest.mock import patch, MagicMock
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import md_converter

class TestExtendedMdConverter(unittest.TestCase):

    def test_parse_markdown_tables_basic(self):
        """Test parsing a simple markdown table."""
        content = """
| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
| Cell 3   | Cell 4   |
"""
        tables = md_converter.parse_markdown_tables(content)
        self.assertEqual(len(tables), 1)
        headers, rows = tables[0]
        self.assertEqual(headers, ["Header 1", "Header 2"])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], ["Cell 1", "Cell 2"])

    def test_parse_markdown_tables_escaped_pipes(self):
        """Test parsing table with escaped pipes."""
        content = r"""
| Col 1 | Col 2 |
|-------|-------|
| Val 1 | Val \| 2 |
| Val \\| Val 4 |
"""
        tables = md_converter.parse_markdown_tables(content)
        self.assertEqual(len(tables), 1)
        headers, rows = tables[0]
        self.assertEqual(rows[0][1], "Val | 2") # unescaped
        self.assertEqual(rows[1][0], "Val \\")  # unescaped backslash

    def test_parse_markdown_tables_empty(self):
        """Test parsing an empty table (headers only)."""
        content = """
| Header 1 | Header 2 |
|----------|----------|
"""
        # Current implementation requires >= 3 lines (header, sep, data).
        # Let's see if this returns empty list or what.
        tables = md_converter.parse_markdown_tables(content)
        # If it returns [], it confirms the behavior I suspected.
        self.assertEqual(tables, [])

    def test_safe_read_file_traversal(self):
        """Test safe_read_file prevents traversal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file outside the base
            secret_file = os.path.join(tmpdir, "secret.txt")
            with open(secret_file, "w") as f:
                f.write("secret")
            
            # Create a base directory inside
            base_dir = os.path.join(tmpdir, "base")
            os.makedirs(base_dir)
            
            # Try to read the secret file using ..
            with self.assertRaises(ValueError) as cm:
                md_converter.safe_read_file(base_dir, "../secret.txt")
            self.assertIn("Security violation", str(cm.exception))

    def test_safe_read_file_symlink_attack(self):
        """Test safe_read_file prevents symlink attacks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            secret_file = os.path.join(tmpdir, "secret.txt")
            with open(secret_file, "w") as f:
                f.write("secret")
            
            base_dir = os.path.join(tmpdir, "base")
            os.makedirs(base_dir)
            
            # Create symlink in base pointing to secret
            symlink_path = os.path.join(base_dir, "link.txt")
            os.symlink(secret_file, symlink_path)
            
            # Try to read the symlink
            with self.assertRaises(ValueError) as cm:
                md_converter.safe_read_file(base_dir, "link.txt")
            self.assertIn("Security violation", str(cm.exception))

    def test_parse_summary_md_nested(self):
        """Test parsing SUMMARY.md with nesting."""
        content = """
# Summary

- [Chapter 1](ch1.md)
  - [Chapter 1.1](ch1_1.md)
    - [Chapter 1.1.1](ch1_1_1.md)
- [Chapter 2](ch2.md)
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            chapters = md_converter.parse_summary_md(temp_path)
            self.assertEqual(len(chapters), 4)
            self.assertEqual(chapters[0].title, "Chapter 1")
            self.assertEqual(chapters[0].level, 0)
            self.assertEqual(chapters[1].title, "Chapter 1.1")
            self.assertEqual(chapters[1].level, 1)
            self.assertEqual(chapters[2].title, "Chapter 1.1.1")
            self.assertEqual(chapters[2].level, 2)
        finally:
            os.remove(temp_path)

    def test_parse_summary_md_parens_in_path(self):
        """Test parsing SUMMARY.md with parentheses in filenames."""
        content = """
- [Title](path/with/(parens).md)
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(content)
            temp_path = f.name
            
        try:
            chapters = md_converter.parse_summary_md(temp_path)
            self.assertEqual(len(chapters), 1)
            self.assertEqual(chapters[0].path, "path/with/(parens).md")
        finally:
            os.remove(temp_path)

    def test_validate_project_path_security(self):
        """Test validate_project_path rejects sensitive paths."""
        # Linux specific
        is_valid, msg = md_converter.validate_project_path("/etc")
        self.assertFalse(is_valid)
        self.assertIn("Access to system directory", msg)
        
        is_valid, msg = md_converter.validate_project_path("/tmp/../etc/passwd")
        self.assertFalse(is_valid)
        
    def test_generate_javascript_highlight_bug_check(self):
        """Check if the generated JS contains the fix for the highlight bug."""
        js = md_converter.generate_javascript({}, "none", "h2", "none", False, False, True)
        
        # The fix involves actually using the fragments to update the DOM.
        # Look for node.parentNode.replaceChild or node.replaceWith
        has_fix = "node.parentNode.replaceChild" in js or "node.replaceWith" in js
        self.assertTrue(has_fix, "JS highlight function is missing the DOM update logic (replaceChild/replaceWith)")

if __name__ == "__main__":
    unittest.main()
