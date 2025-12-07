"""
Tests for reset endpoint.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import shutil

from src.api.reset import clear_artifacts, ARTIFACTS_DIR


class TestClearArtifacts:
    """Tests for clear_artifacts function."""

    def test_clear_artifacts_creates_dir_if_not_exists(self):
        """Test that clear_artifacts creates directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "nonexistent"
            
            with patch("src.api.reset.ARTIFACTS_DIR", test_dir):
                clear_artifacts()
                assert test_dir.exists()
                assert test_dir.is_dir()

    def test_clear_artifacts_removes_files(self):
        """Test that clear_artifacts removes files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "artifacts"
            test_dir.mkdir()
            
            # Create test files
            (test_dir / "file1.json").write_text("test1")
            (test_dir / "file2.txt").write_text("test2")
            
            with patch("src.api.reset.ARTIFACTS_DIR", test_dir):
                clear_artifacts()
                
                # Directory should exist but be empty
                assert test_dir.exists()
                assert list(test_dir.iterdir()) == []

    def test_clear_artifacts_removes_directories(self):
        """Test that clear_artifacts removes subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "artifacts"
            test_dir.mkdir()
            
            # Create subdirectories with files
            subdir1 = test_dir / "subdir1"
            subdir1.mkdir()
            (subdir1 / "file.txt").write_text("content")
            
            subdir2 = test_dir / "subdir2"
            subdir2.mkdir()
            
            with patch("src.api.reset.ARTIFACTS_DIR", test_dir):
                clear_artifacts()
                
                assert test_dir.exists()
                assert list(test_dir.iterdir()) == []

    def test_clear_artifacts_handles_symlinks(self):
        """Test that clear_artifacts removes symlinks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "artifacts"
            test_dir.mkdir()
            
            # Create a file and a symlink to it
            target_file = test_dir / "target.txt"
            target_file.write_text("content")
            
            symlink = test_dir / "link.txt"
            symlink.symlink_to(target_file)
            
            with patch("src.api.reset.ARTIFACTS_DIR", test_dir):
                clear_artifacts()
                
                assert test_dir.exists()
                assert list(test_dir.iterdir()) == []

    def test_clear_artifacts_handles_errors_gracefully(self):
        """Test that clear_artifacts doesn't crash on errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "artifacts"
            test_dir.mkdir()
            
            # Create a file
            test_file = test_dir / "test.txt"
            test_file.write_text("content")
            
            # Mock unlink to raise an exception
            with patch("src.api.reset.ARTIFACTS_DIR", test_dir):
                with patch.object(Path, "unlink", side_effect=PermissionError("Test error")):
                    # Should not raise an exception
                    clear_artifacts()

    def test_clear_artifacts_handles_directory_errors(self):
        """Test that clear_artifacts handles errors when removing directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "artifacts"
            test_dir.mkdir()
            
            # Create a subdirectory
            subdir = test_dir / "subdir"
            subdir.mkdir()
            
            with patch("src.api.reset.ARTIFACTS_DIR", test_dir):
                with patch("shutil.rmtree", side_effect=PermissionError("Test error")):
                    # Should not raise an exception
                    clear_artifacts()

    def test_clear_artifacts_handles_top_level_exception(self):
        """Test that clear_artifacts handles exceptions at the top level."""
        with patch("src.api.reset.ARTIFACTS_DIR", Path("/nonexistent/path")):
            with patch.object(Path, "exists", side_effect=Exception("Test error")):
                # Should not raise an exception
                clear_artifacts()

    def test_clear_artifacts_mixed_content(self):
        """Test clear_artifacts with mixed files and directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "artifacts"
            test_dir.mkdir()
            
            # Create mixed content
            (test_dir / "file1.txt").write_text("content1")
            
            subdir = test_dir / "subdir"
            subdir.mkdir()
            (subdir / "nested.txt").write_text("nested")
            
            (test_dir / "file2.json").write_text("{}")
            
            with patch("src.api.reset.ARTIFACTS_DIR", test_dir):
                clear_artifacts()
                
                assert test_dir.exists()
                assert list(test_dir.iterdir()) == []
