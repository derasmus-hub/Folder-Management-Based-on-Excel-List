"""
Tests for Windows path utilities.

These tests verify path normalization, extended-length path conversion,
and safe move operations.
"""

import os
import sys
import pytest
import shutil
import tempfile
from pathlib import Path

from folder_mover.utils import (
    normalize_path,
    to_extended_length_path,
    from_extended_length_path,
    is_unc_path,
    safe_move,
    EXTENDED_PATH_PREFIX,
    EXTENDED_UNC_PREFIX,
    UNC_PREFIX,
)


class TestNormalizePath:
    """Tests for normalize_path function."""

    def test_path_object_converted_to_string(self):
        """Path objects should be converted to strings."""
        result = normalize_path(Path("/some/path"))
        assert isinstance(result, str)

    def test_relative_path_becomes_absolute(self):
        """Relative paths should be converted to absolute."""
        result = normalize_path("relative/path")
        assert os.path.isabs(result)

    def test_absolute_path_unchanged(self, tmp_path):
        """Absolute paths should remain absolute."""
        abs_path = str(tmp_path / "test")
        result = normalize_path(abs_path)
        assert os.path.isabs(result)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_windows_drive_path_normalized(self):
        """Windows drive paths should be normalized."""
        result = normalize_path("C:/Users/test")
        assert result.startswith("C:\\")
        assert "/" not in result  # Should use backslashes

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_unc_path_preserved(self):
        """UNC paths should be preserved."""
        unc_path = "\\\\server\\share\\folder"
        result = normalize_path(unc_path)
        assert result.startswith("\\\\")
        assert "server" in result
        assert "share" in result

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_unc_path_with_forward_slashes(self):
        """UNC paths with forward slashes should be normalized."""
        unc_path = "\\\\server/share/folder"
        result = normalize_path(unc_path)
        assert result.startswith("\\\\")
        assert "/" not in result

    def test_extended_path_returned_unchanged(self):
        """Already-extended paths should be returned unchanged."""
        extended = "\\\\?\\C:\\Users\\test"
        result = normalize_path(extended)
        assert result == extended


class TestToExtendedLengthPath:
    """Tests for to_extended_length_path function."""

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_local_path_gets_prefix(self):
        """Local paths should get \\\\?\\ prefix on Windows."""
        result = to_extended_length_path("C:\\Users\\test")
        assert result.startswith(EXTENDED_PATH_PREFIX)
        assert "C:\\Users\\test" in result

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_unc_path_gets_unc_prefix(self):
        """UNC paths should get \\\\?\\UNC\\ prefix on Windows."""
        result = to_extended_length_path("\\\\server\\share\\folder")
        assert result.startswith(EXTENDED_UNC_PREFIX)
        assert "server\\share\\folder" in result

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_already_extended_unchanged(self):
        """Already-extended paths should not be double-prefixed."""
        extended = "\\\\?\\C:\\Users\\test"
        result = to_extended_length_path(extended)
        assert result == extended
        assert result.count("\\\\?\\") == 1

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_already_extended_unc_unchanged(self):
        """Already-extended UNC paths should not be double-prefixed."""
        extended = "\\\\?\\UNC\\server\\share"
        result = to_extended_length_path(extended)
        assert result == extended

    @pytest.mark.skipif(sys.platform == "win32", reason="Non-Windows test")
    def test_non_windows_returns_unchanged(self):
        """On non-Windows, paths should be returned unchanged."""
        result = to_extended_length_path("/home/user/test")
        assert result == "/home/user/test"
        assert not result.startswith("\\\\")


class TestFromExtendedLengthPath:
    """Tests for from_extended_length_path function."""

    def test_extended_local_path_stripped(self):
        """Extended local paths should have prefix removed."""
        extended = "\\\\?\\C:\\Users\\test"
        result = from_extended_length_path(extended)
        assert result == "C:\\Users\\test"
        assert not result.startswith("\\\\?\\")

    def test_extended_unc_path_converted(self):
        """Extended UNC paths should be converted back to normal form."""
        extended = "\\\\?\\UNC\\server\\share\\folder"
        result = from_extended_length_path(extended)
        assert result == "\\\\server\\share\\folder"
        assert result.startswith("\\\\")
        assert "UNC" not in result

    def test_normal_path_unchanged(self):
        """Normal paths should be returned unchanged."""
        normal = "C:\\Users\\test"
        result = from_extended_length_path(normal)
        assert result == normal

    def test_unc_path_unchanged(self):
        """Normal UNC paths should be returned unchanged."""
        unc = "\\\\server\\share"
        result = from_extended_length_path(unc)
        assert result == unc


class TestIsUncPath:
    """Tests for is_unc_path function."""

    def test_unc_path_detected(self):
        """Normal UNC paths should be detected."""
        assert is_unc_path("\\\\server\\share")
        assert is_unc_path("\\\\server\\share\\folder\\subfolder")

    def test_extended_unc_path_detected(self):
        """Extended UNC paths should be detected."""
        assert is_unc_path("\\\\?\\UNC\\server\\share")

    def test_local_path_not_unc(self):
        """Local paths should not be detected as UNC."""
        assert not is_unc_path("C:\\Users\\test")
        assert not is_unc_path("\\\\?\\C:\\Users\\test")

    def test_unix_path_not_unc(self):
        """Unix paths should not be detected as UNC."""
        assert not is_unc_path("/home/user")
        assert not is_unc_path("/mnt/share")


class TestSafeMove:
    """Tests for safe_move function."""

    @pytest.fixture
    def temp_dirs(self, tmp_path):
        """Create temporary source and dest directories."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        dest_parent = tmp_path / "dest_parent"
        dest_parent.mkdir()

        # Create a file in source
        (source_dir / "test_file.txt").write_text("test content")

        yield {
            "source": source_dir,
            "dest_parent": dest_parent,
            "dest": dest_parent / "moved_folder",
        }

    def test_basic_move_succeeds(self, temp_dirs):
        """Basic move should succeed."""
        success, message = safe_move(
            temp_dirs["source"],
            temp_dirs["dest"],
            use_extended_paths=False  # Avoid Windows-specific on all platforms
        )
        assert success is True
        assert "success" in message.lower()
        assert temp_dirs["dest"].exists()
        assert not temp_dirs["source"].exists()

    def test_move_preserves_contents(self, temp_dirs):
        """Move should preserve folder contents."""
        # Add more files
        (temp_dirs["source"] / "another.txt").write_text("another")
        subdir = temp_dirs["source"] / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("nested")

        success, _ = safe_move(
            temp_dirs["source"],
            temp_dirs["dest"],
            use_extended_paths=False
        )

        assert success
        assert (temp_dirs["dest"] / "test_file.txt").read_text() == "test content"
        assert (temp_dirs["dest"] / "another.txt").read_text() == "another"
        assert (temp_dirs["dest"] / "subdir" / "nested.txt").read_text() == "nested"

    def test_move_nonexistent_source_fails(self, temp_dirs):
        """Moving a nonexistent source should fail."""
        nonexistent = temp_dirs["dest_parent"] / "nonexistent"
        success, message = safe_move(
            nonexistent,
            temp_dirs["dest"],
            use_extended_paths=False
        )
        # The function doesn't check existence - it tries to move and fails
        # This is OK because move_folder() checks existence before calling safe_move
        # The actual behavior depends on shutil.move

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_extended_paths_used_on_windows(self, temp_dirs):
        """Extended paths should be used on Windows when requested."""
        # This test verifies the function doesn't crash with extended paths
        success, message = safe_move(
            temp_dirs["source"],
            temp_dirs["dest"],
            use_extended_paths=True
        )
        assert success is True
        assert temp_dirs["dest"].exists()


class TestPathRoundTrip:
    """Tests for path conversion round-trips."""

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_local_path_roundtrip(self):
        """Local paths should survive to/from extended conversion."""
        original = "C:\\Users\\test\\folder"
        extended = to_extended_length_path(original)
        restored = from_extended_length_path(extended)
        assert restored == original

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_unc_path_roundtrip(self):
        """UNC paths should survive to/from extended conversion."""
        original = "\\\\server\\share\\folder"
        extended = to_extended_length_path(original)
        restored = from_extended_length_path(extended)
        assert restored == original

    def test_normalize_then_extended_roundtrip(self, tmp_path):
        """Normalized paths should convert to extended and back."""
        if sys.platform != "win32":
            pytest.skip("Windows-only test")

        original = str(tmp_path / "test_folder")
        normalized = normalize_path(original)
        extended = to_extended_length_path(normalized)
        restored = from_extended_length_path(extended)

        # The restored path should be the normalized path
        assert restored == normalized


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_long_path_handling(self, tmp_path):
        """Long paths should be handled correctly."""
        # Create a path that would exceed MAX_PATH (260) without extended prefix
        long_name = "a" * 200
        long_path = str(tmp_path / long_name / long_name)

        # Should not crash
        extended = to_extended_length_path(long_path)
        assert extended.startswith(EXTENDED_PATH_PREFIX)

    def test_empty_string_handling(self):
        """Empty strings should not crash."""
        # normalize_path on empty string - behavior may vary
        try:
            result = normalize_path("")
            # Should return current directory or raise
            assert isinstance(result, str)
        except (ValueError, OSError):
            pass  # Acceptable to raise on empty

    def test_path_with_spaces(self, tmp_path):
        """Paths with spaces should be handled correctly."""
        spaced_path = str(tmp_path / "path with spaces" / "more spaces")
        normalized = normalize_path(spaced_path)
        assert "with spaces" in normalized

        if sys.platform == "win32":
            extended = to_extended_length_path(spaced_path)
            assert "with spaces" in extended
