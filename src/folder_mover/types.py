"""
Type definitions and data classes for the folder mover application.

This module defines:
- FolderEntry: Data class for scanned folder info (name + path)
- FolderMatch: Data class representing a matched folder
- MoveResult: Data class representing the result of a move operation
- MoveStatus: Enum for move operation outcomes
- ReportEntry: Data class for CSV report rows
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


@dataclass(slots=True)
class FolderEntry:
    """
    Represents a folder discovered during scanning.

    Attributes:
        name: The folder's basename (e.g., "Case_00123_Documents")
        path: The full absolute path to the folder
    """
    name: str
    path: str

    def __hash__(self):
        return hash(self.path)

    def __eq__(self, other):
        if not isinstance(other, FolderEntry):
            return False
        return self.path == other.path


class MoveStatus(Enum):
    """Status of a folder move operation."""
    SUCCESS = "success"              # Moved successfully
    SUCCESS_RENAMED = "success_renamed"  # Moved with suffix due to collision
    SKIPPED_MISSING = "skipped_missing"  # Source no longer exists
    SKIPPED_EXISTS = "skipped_exists"    # Already at destination
    ERROR = "error"                  # Failed due to error
    DRY_RUN = "dry_run"              # Would move (dry run mode)
    DRY_RUN_RENAMED = "dry_run_renamed"  # Would move with rename (dry run)


@dataclass
class FolderMatch:
    """Represents a folder that matched a CaseID."""
    case_id: str
    source_path: str
    folder_name: str


@dataclass
class MoveResult:
    """Result of a move operation."""
    case_id: str
    source_path: str
    dest_path: Optional[str]
    status: MoveStatus
    message: str


class ReportStatus(Enum):
    """Status values for CSV report (human-readable)."""
    MOVED = "MOVED"                      # Successfully moved
    MOVED_RENAMED = "MOVED_RENAMED"      # Moved with rename due to collision
    FOUND_DRYRUN = "FOUND_DRYRUN"        # Would move (dry run)
    FOUND_DRYRUN_RENAMED = "FOUND_DRYRUN_RENAMED"  # Would move with rename
    NOT_FOUND = "NOT_FOUND"              # CaseID had no folder matches
    MULTIPLE_MATCHES = "MULTIPLE_MATCHES"  # CaseID matched multiple folders
    SKIPPED_MISSING = "SKIPPED_MISSING"  # Source no longer exists
    SKIPPED_EXISTS = "SKIPPED_EXISTS"    # Already at destination
    ERROR = "ERROR"                      # Operation failed

    @classmethod
    def from_move_status(cls, status: MoveStatus, is_multiple: bool = False):
        """Convert MoveStatus to ReportStatus."""
        if is_multiple:
            return cls.MULTIPLE_MATCHES

        mapping = {
            MoveStatus.SUCCESS: cls.MOVED,
            MoveStatus.SUCCESS_RENAMED: cls.MOVED_RENAMED,
            MoveStatus.SKIPPED_MISSING: cls.SKIPPED_MISSING,
            MoveStatus.SKIPPED_EXISTS: cls.SKIPPED_EXISTS,
            MoveStatus.ERROR: cls.ERROR,
            MoveStatus.DRY_RUN: cls.FOUND_DRYRUN,
            MoveStatus.DRY_RUN_RENAMED: cls.FOUND_DRYRUN_RENAMED,
        }
        return mapping.get(status, cls.ERROR)


@dataclass
class ReportEntry:
    """Entry for the CSV report."""
    timestamp: str
    case_id: str
    status: str
    source_path: str
    dest_path: str
    message: str
