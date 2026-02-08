"""
Unit tests for CLI functions.
"""

import tempfile
from pathlib import Path

import pytest

from folder_mover.cli import load_moved_paths_from_report


class TestLoadMovedPathsFromReport:
    """Tests for load_moved_paths_from_report function."""

    def test_load_moved_paths(self):
        """Loads paths with MOVED status."""
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.csv"
            report.write_text(
                "timestamp,case_id,status,source_path,dest_path,message\n"
                "2024-01-01,001,MOVED,C:\\Source\\Folder1,C:\\Dest\\Folder1,success\n"
                "2024-01-01,002,MOVED_RENAMED,C:\\Source\\Folder2,C:\\Dest\\Folder2_1,renamed\n"
                "2024-01-01,003,NOT_FOUND,,,not found\n"
            )

            paths = load_moved_paths_from_report(report)

            assert len(paths) == 2
            assert "C:\\Source\\Folder1" in paths
            assert "C:\\Source\\Folder2" in paths

    def test_ignores_non_moved_status(self):
        """Ignores paths that weren't moved."""
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.csv"
            report.write_text(
                "timestamp,case_id,status,source_path,dest_path,message\n"
                "2024-01-01,001,ERROR,C:\\Source\\Failed,,error\n"
                "2024-01-01,002,SKIPPED_EXISTS,C:\\Source\\Skip,C:\\Dest\\Skip,exists\n"
                "2024-01-01,003,NOT_FOUND,,,not found\n"
            )

            paths = load_moved_paths_from_report(report)

            assert len(paths) == 0

    def test_file_not_found(self):
        """Raises error for missing file."""
        with pytest.raises(FileNotFoundError):
            load_moved_paths_from_report(Path("/nonexistent/report.csv"))

    def test_missing_columns(self):
        """Raises error for missing columns."""
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.csv"
            report.write_text("wrong,columns,here\n1,2,3\n")

            with pytest.raises(ValueError) as exc_info:
                load_moved_paths_from_report(report)

            assert "missing required columns" in str(exc_info.value)

    def test_empty_file(self):
        """Raises error for empty file."""
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.csv"
            report.write_text("")

            with pytest.raises(ValueError) as exc_info:
                load_moved_paths_from_report(report)

            assert "empty or invalid" in str(exc_info.value)

    def test_skips_empty_source_paths(self):
        """Skips rows with empty source paths."""
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.csv"
            report.write_text(
                "timestamp,case_id,status,source_path,dest_path,message\n"
                "2024-01-01,001,MOVED,C:\\Source\\Folder1,C:\\Dest\\Folder1,success\n"
                "2024-01-01,002,MOVED,,,empty source\n"
            )

            paths = load_moved_paths_from_report(report)

            assert len(paths) == 1
            assert "C:\\Source\\Folder1" in paths

    def test_handles_parameter_rows(self):
        """Handles reports with PARAMETER rows at top."""
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.csv"
            report.write_text(
                "timestamp,case_id,status,source_path,dest_path,message\n"
                "2024-01-01,,PARAMETER,,,version=1.0.0\n"
                "2024-01-01,,PARAMETER,,,dry_run=False\n"
                "2024-01-01,,PARAMETER,,,--- END PARAMETERS ---\n"
                "2024-01-01,001,MOVED,C:\\Source\\Folder1,C:\\Dest\\Folder1,success\n"
            )

            paths = load_moved_paths_from_report(report)

            assert len(paths) == 1
            assert "C:\\Source\\Folder1" in paths

    def test_strips_whitespace(self):
        """Strips whitespace from status and paths."""
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.csv"
            report.write_text(
                "timestamp,case_id,status,source_path,dest_path,message\n"
                "2024-01-01,001, MOVED ,  C:\\Source\\Folder1  ,C:\\Dest\\Folder1,success\n"
            )

            paths = load_moved_paths_from_report(report)

            assert len(paths) == 1
            assert "C:\\Source\\Folder1" in paths
