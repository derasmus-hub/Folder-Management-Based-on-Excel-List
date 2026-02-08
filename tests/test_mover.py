"""
Unit tests for the folder mover.
"""

import tempfile
from pathlib import Path

import pytest

from folder_mover.mover import (
    FolderMover,
    move_folder,
    resolve_destination,
)
from folder_mover.types import FolderMatch, MoveStatus


class TestResolveDestination:
    """Tests for resolve_destination function."""

    def test_no_collision(self):
        """Returns original path when no collision."""
        with tempfile.TemporaryDirectory() as tmp:
            result = resolve_destination(tmp, "MyFolder")
            assert result == str(Path(tmp) / "MyFolder")

    def test_collision_with_existing_folder(self):
        """Adds suffix when folder already exists."""
        with tempfile.TemporaryDirectory() as tmp:
            # Create existing folder
            (Path(tmp) / "MyFolder").mkdir()

            result = resolve_destination(tmp, "MyFolder")
            assert result == str(Path(tmp) / "MyFolder_1")

    def test_multiple_collisions(self):
        """Increments suffix for multiple collisions."""
        with tempfile.TemporaryDirectory() as tmp:
            # Create existing folders
            (Path(tmp) / "MyFolder").mkdir()
            (Path(tmp) / "MyFolder_1").mkdir()
            (Path(tmp) / "MyFolder_2").mkdir()

            result = resolve_destination(tmp, "MyFolder")
            assert result == str(Path(tmp) / "MyFolder_3")

    def test_collision_with_claimed_names(self):
        """Respects claimed names set."""
        with tempfile.TemporaryDirectory() as tmp:
            claimed = {"MyFolder", "MyFolder_1"}

            result = resolve_destination(tmp, "MyFolder", claimed)
            assert result == str(Path(tmp) / "MyFolder_2")

    def test_mixed_disk_and_claimed_collision(self):
        """Handles both disk and claimed name collisions."""
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "MyFolder").mkdir()
            (Path(tmp) / "MyFolder_1").mkdir()  # On disk
            claimed = {"MyFolder_2"}  # Claimed in session

            result = resolve_destination(tmp, "MyFolder", claimed)
            assert result == str(Path(tmp) / "MyFolder_3")


class TestMoveFolder:
    """Tests for move_folder function."""

    def test_successful_move(self):
        """Successfully moves folder."""
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "source"
            dest = Path(tmp) / "dest"
            src.mkdir()
            (src / "file.txt").write_text("content")

            result = move_folder(src, dest)

            assert result.status == MoveStatus.SUCCESS
            assert not src.exists()
            assert dest.exists()
            assert (dest / "file.txt").read_text() == "content"

    def test_source_missing(self):
        """Reports missing source."""
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "nonexistent"
            dest = Path(tmp) / "dest"

            result = move_folder(src, dest)

            assert result.status == MoveStatus.SKIPPED_MISSING
            assert "no longer exists" in result.message

    def test_destination_exists(self):
        """Reports existing destination."""
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "source"
            dest = Path(tmp) / "dest"
            src.mkdir()
            dest.mkdir()

            result = move_folder(src, dest)

            assert result.status == MoveStatus.SKIPPED_EXISTS
            assert src.exists()  # Source untouched

    def test_dry_run_no_move(self):
        """Dry run doesn't actually move."""
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "source"
            dest = Path(tmp) / "dest"
            src.mkdir()

            result = move_folder(src, dest, dry_run=True)

            assert result.status == MoveStatus.DRY_RUN
            assert src.exists()  # Still there
            assert not dest.exists()  # Not created

    def test_dry_run_different_dest_name(self):
        """Dry run works with different dest name (rename detection in FolderMover)."""
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "source"
            dest = Path(tmp) / "dest_different"
            src.mkdir()

            # Low-level move_folder doesn't detect renames - just reports DRY_RUN
            result = move_folder(src, dest, dry_run=True)

            assert result.status == MoveStatus.DRY_RUN
            assert src.exists()  # Still there

    def test_move_with_contents(self):
        """Moves folder with all contents."""
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "source"
            src.mkdir()
            (src / "subdir").mkdir()
            (src / "file1.txt").write_text("content1")
            (src / "subdir" / "file2.txt").write_text("content2")

            dest = Path(tmp) / "dest"
            result = move_folder(src, dest)

            assert result.status == MoveStatus.SUCCESS
            assert (dest / "file1.txt").read_text() == "content1"
            assert (dest / "subdir" / "file2.txt").read_text() == "content2"

    def test_source_is_file_error(self):
        """Reports error when source is a file."""
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "file.txt"
            src.write_text("content")
            dest = Path(tmp) / "dest"

            result = move_folder(src, dest)

            assert result.status == MoveStatus.ERROR
            assert "not a directory" in result.message


class TestFolderMover:
    """Tests for FolderMover class."""

    def test_move_single_folder(self):
        """Moves a single matched folder."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            src = base / "source" / "Case_00123"
            dest_root = base / "dest"
            src.mkdir(parents=True)
            dest_root.mkdir()

            match = FolderMatch(
                case_id="00123",
                source_path=str(src),
                folder_name="Case_00123"
            )

            mover = FolderMover(dest_root)
            result = mover.move_folder(match)

            assert result.status == MoveStatus.SUCCESS
            assert result.case_id == "00123"
            assert (dest_root / "Case_00123").exists()

    def test_move_with_collision(self):
        """Handles collision by adding suffix."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            src = base / "source" / "Case_00123"
            dest_root = base / "dest"
            src.mkdir(parents=True)
            dest_root.mkdir()
            (dest_root / "Case_00123").mkdir()  # Create collision

            match = FolderMatch(
                case_id="00123",
                source_path=str(src),
                folder_name="Case_00123"
            )

            mover = FolderMover(dest_root)
            result = mover.move_folder(match)

            assert result.status == MoveStatus.SUCCESS_RENAMED
            assert (dest_root / "Case_00123_1").exists()

    def test_move_all_basic(self):
        """Moves multiple folders."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            src_root = base / "source"
            dest_root = base / "dest"
            src_root.mkdir()
            dest_root.mkdir()

            # Create source folders
            (src_root / "Case_001").mkdir()
            (src_root / "Case_002").mkdir()

            matches = [
                FolderMatch("001", str(src_root / "Case_001"), "Case_001"),
                FolderMatch("002", str(src_root / "Case_002"), "Case_002"),
            ]

            mover = FolderMover(dest_root)
            results = mover.move_all(matches)

            assert len(results) == 2
            assert all(r.status == MoveStatus.SUCCESS for r in results)
            assert (dest_root / "Case_001").exists()
            assert (dest_root / "Case_002").exists()

    def test_move_all_with_batch_collision(self):
        """Handles collisions between items in same batch."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            dest_root = base / "dest"
            dest_root.mkdir()

            # Create two source folders with same name in different locations
            src1 = base / "loc1" / "SameName"
            src2 = base / "loc2" / "SameName"
            src1.mkdir(parents=True)
            src2.mkdir(parents=True)

            matches = [
                FolderMatch("001", str(src1), "SameName"),
                FolderMatch("002", str(src2), "SameName"),
            ]

            mover = FolderMover(dest_root)
            results = mover.move_all(matches)

            assert len(results) == 2
            assert results[0].status == MoveStatus.SUCCESS
            assert results[1].status == MoveStatus.SUCCESS_RENAMED
            assert (dest_root / "SameName").exists()
            assert (dest_root / "SameName_1").exists()

    def test_dry_run_mode(self):
        """Dry run doesn't move anything."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            src = base / "source" / "Case_00123"
            dest_root = base / "dest"
            src.mkdir(parents=True)
            dest_root.mkdir()

            match = FolderMatch("00123", str(src), "Case_00123")

            mover = FolderMover(dest_root, dry_run=True)
            result = mover.move_folder(match)

            assert result.status == MoveStatus.DRY_RUN
            assert src.exists()
            assert not (dest_root / "Case_00123").exists()

    def test_max_moves_limit(self):
        """Respects max_moves limit."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            dest_root = base / "dest"
            dest_root.mkdir()

            # Create 5 source folders
            matches = []
            for i in range(5):
                src = base / f"src_{i}" / f"Folder_{i}"
                src.mkdir(parents=True)
                matches.append(FolderMatch(f"{i}", str(src), f"Folder_{i}"))

            mover = FolderMover(dest_root, max_moves=3)
            results = mover.move_all(matches)

            assert len(results) == 3
            assert (dest_root / "Folder_0").exists()
            assert (dest_root / "Folder_1").exists()
            assert (dest_root / "Folder_2").exists()
            assert not (dest_root / "Folder_3").exists()
            assert not (dest_root / "Folder_4").exists()

    def test_get_stats(self):
        """Tracks statistics correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            dest_root = base / "dest"
            dest_root.mkdir()

            # One existing (will succeed)
            src1 = base / "src1"
            src1.mkdir()

            # One missing (will skip)
            src2 = base / "src2"  # Don't create

            matches = [
                FolderMatch("001", str(src1), "Folder1"),
                FolderMatch("002", str(src2), "Folder2"),
            ]

            mover = FolderMover(dest_root)
            mover.move_all(matches)

            stats = mover.get_stats()
            assert stats["success"] == 1
            assert stats["skipped_missing"] == 1

    def test_get_summary(self):
        """Generates readable summary."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            dest_root = base / "dest"
            dest_root.mkdir()

            src = base / "src"
            src.mkdir()

            match = FolderMatch("001", str(src), "Folder")
            mover = FolderMover(dest_root)
            mover.move_folder(match)

            summary = mover.get_summary()
            assert "Move Summary" in summary
            assert "Moved: 1" in summary

    def test_reset_stats(self):
        """Reset clears stats and claimed names."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            dest_root = base / "dest"
            dest_root.mkdir()

            src = base / "src"
            src.mkdir()

            match = FolderMatch("001", str(src), "Folder")
            mover = FolderMover(dest_root)
            mover.move_folder(match)

            assert sum(mover.get_stats().values()) > 0
            assert len(mover._claimed_names) > 0

            mover.reset_stats()

            assert sum(mover.get_stats().values()) == 0
            assert len(mover._claimed_names) == 0


class TestIdempotency:
    """Tests for idempotent behavior."""

    def test_already_moved_skipped(self):
        """Source that no longer exists is skipped."""
        with tempfile.TemporaryDirectory() as tmp:
            dest_root = Path(tmp) / "dest"
            dest_root.mkdir()

            match = FolderMatch(
                case_id="00123",
                source_path="/nonexistent/source/path",
                folder_name="Case_00123"
            )

            mover = FolderMover(dest_root)
            result = mover.move_folder(match)

            assert result.status == MoveStatus.SKIPPED_MISSING

    def test_run_twice_idempotent(self):
        """Running twice on same data is safe."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            src = base / "source" / "Case_00123"
            dest_root = base / "dest"
            src.mkdir(parents=True)
            dest_root.mkdir()

            match = FolderMatch("00123", str(src), "Case_00123")

            # First run - moves the folder
            mover1 = FolderMover(dest_root)
            result1 = mover1.move_folder(match)
            assert result1.status == MoveStatus.SUCCESS

            # Second run - source is gone
            mover2 = FolderMover(dest_root)
            result2 = mover2.move_folder(match)
            assert result2.status == MoveStatus.SKIPPED_MISSING


class TestEdgeCases:
    """Tests for edge cases."""

    def test_special_characters_in_name(self):
        """Handles special characters in folder names."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            # Note: some characters aren't allowed on Windows
            src = base / "Case #123 (2023)"
            dest_root = base / "dest"
            src.mkdir()
            dest_root.mkdir()

            match = FolderMatch("123", str(src), "Case #123 (2023)")
            mover = FolderMover(dest_root)
            result = mover.move_folder(match)

            assert result.status == MoveStatus.SUCCESS

    def test_deeply_nested_source(self):
        """Handles deeply nested source folders."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            # Create deep path
            src = base / "a" / "b" / "c" / "d" / "e" / "Case_001"
            src.mkdir(parents=True)
            dest_root = base / "dest"
            dest_root.mkdir()

            match = FolderMatch("001", str(src), "Case_001")
            mover = FolderMover(dest_root)
            result = mover.move_folder(match)

            assert result.status == MoveStatus.SUCCESS
            assert (dest_root / "Case_001").exists()

    def test_empty_source_folder(self):
        """Handles empty source folder."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            src = base / "EmptyFolder"
            src.mkdir()
            dest_root = base / "dest"
            dest_root.mkdir()

            match = FolderMatch("001", str(src), "EmptyFolder")
            mover = FolderMover(dest_root)
            result = mover.move_folder(match)

            assert result.status == MoveStatus.SUCCESS
            assert (dest_root / "EmptyFolder").exists()

    def test_progress_callback(self):
        """Progress callback is called correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            dest_root = base / "dest"
            dest_root.mkdir()

            # Create source folders
            matches = []
            for i in range(3):
                src = base / f"src_{i}"
                src.mkdir()
                matches.append(FolderMatch(f"{i}", str(src), f"Folder_{i}"))

            progress_calls = []

            def callback(current, total, match):
                progress_calls.append((current, total, match.case_id))

            mover = FolderMover(dest_root)
            mover.move_all(matches, progress_callback=callback)

            assert len(progress_calls) == 3
            assert progress_calls[0] == (1, 3, "0")
            assert progress_calls[1] == (2, 3, "1")
            assert progress_calls[2] == (3, 3, "2")
