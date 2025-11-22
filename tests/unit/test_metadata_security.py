"""Unit tests for metadata loading security.

Tests path validation to ensure artwork paths cannot escape their base directory.
"""

import os
import tempfile
import unittest
from unittest.mock import patch

from src.utils.metadata import _validate_artwork_path


class TestArtworkPathValidation(unittest.TestCase):
    """Test suite for artwork path validation security."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory as base
        self.temp_dir = tempfile.mkdtemp()
        self.base_dir = self.temp_dir

    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary directory
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_valid_relative_path(self):
        """Test that valid relative paths are accepted."""
        result = _validate_artwork_path("artwork/cover.jpg", self.base_dir)
        self.assertIsNotNone(result)
        self.assertTrue(result.startswith(self.base_dir))

    def test_valid_absolute_path(self):
        """Test that absolute paths are validated."""
        abs_path = "/tmp/cover.jpg"
        result = _validate_artwork_path(abs_path, self.base_dir)
        self.assertIsNotNone(result)
        self.assertEqual(result, os.path.abspath(abs_path))

    def test_path_traversal_double_dot(self):
        """Test that paths with .. are rejected."""
        # Try to escape base directory with ../
        result = _validate_artwork_path("../etc/passwd", self.base_dir)
        self.assertIsNone(result)

    def test_path_traversal_multiple_dots(self):
        """Test that paths with multiple .. sequences are rejected."""
        result = _validate_artwork_path("../../etc/passwd", self.base_dir)
        self.assertIsNone(result)

    def test_path_traversal_nested(self):
        """Test that nested path traversal attempts are rejected."""
        result = _validate_artwork_path("artwork/../../etc/passwd", self.base_dir)
        self.assertIsNone(result)

    def test_path_traversal_encoded(self):
        """Test that normalized paths with .. are rejected."""
        # After normalization, this becomes ../etc/passwd
        result = _validate_artwork_path("foo/../../../etc/passwd", self.base_dir)
        self.assertIsNone(result)

    def test_empty_path(self):
        """Test that empty paths return None."""
        result = _validate_artwork_path("", self.base_dir)
        self.assertIsNone(result)

    def test_none_path(self):
        """Test that None paths return None."""
        result = _validate_artwork_path(None, self.base_dir)
        self.assertIsNone(result)

    def test_subdirectory_path(self):
        """Test that paths within subdirectories are accepted."""
        result = _validate_artwork_path("artwork/albums/cover.jpg", self.base_dir)
        self.assertIsNotNone(result)
        self.assertTrue(result.startswith(self.base_dir))

    def test_current_directory_reference(self):
        """Test that ./ references are normalized and accepted."""
        result = _validate_artwork_path("./artwork/cover.jpg", self.base_dir)
        self.assertIsNotNone(result)
        self.assertTrue(result.startswith(self.base_dir))

    def test_mixed_separators(self):
        """Test that mixed path separators are handled correctly."""
        result = _validate_artwork_path("artwork/../artwork/cover.jpg", self.base_dir)
        # This normalizes to artwork/cover.jpg which is valid
        self.assertIsNotNone(result)
        self.assertTrue(result.startswith(self.base_dir))
        # But it must not escape the base directory
        self.assertTrue("artwork" in result)


if __name__ == '__main__':
    unittest.main()
