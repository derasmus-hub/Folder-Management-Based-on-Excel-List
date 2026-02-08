"""
Folder mover for relocating matched folders to the destination.

This module is responsible for:
- Moving folders from source to destination root
- Handling name collisions with _1, _2, etc. suffixes
- Supporting dry-run mode (no actual moves)
- Ensuring idempotency (skip if already moved or source missing)
- Catching and recording errors (permissions, locked files, etc.)
- Logging all operations
- Returning detailed results for reporting
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

from .types import FolderMatch, MoveResult, MoveStatus

logger = logging.getLogger(__name__)


def resolve_destination(
    dest_root: Union[str, Path],
    folder_name: str,
    existing_names: Optional[Set[str]] = None
) -> str:
    """
    Resolve a unique destination path for a folder.

    If the target path already exists (or is in existing_names), appends
    _1, _2, etc. until a unique name is found.

    Args:
        dest_root: The destination root directory
        folder_name: The original folder name to place in dest_root
        existing_names: Optional set of names already claimed in this session
                        (for tracking pending moves in dry-run or batch)

    Returns:
        The full destination path (unique, may have suffix)
    """
    dest_root = Path(dest_root)
    existing_names = existing_names or set()

    # Try the original name first
    candidate = dest_root / folder_name
    if not candidate.exists() and folder_name not in existing_names:
        return str(candidate)

    # Find a unique suffix
    counter = 1
    while True:
        suffixed_name = f"{folder_name}_{counter}"
        candidate = dest_root / suffixed_name
        if not candidate.exists() and suffixed_name not in existing_names:
            return str(candidate)
        counter += 1

        # Safety limit to prevent infinite loops
        if counter > 10000:
            raise RuntimeError(
                f"Could not find unique name for '{folder_name}' "
                f"after 10000 attempts"
            )


def move_folder(
    src_path: Union[str, Path],
    dest_path: Union[str, Path],
    dry_run: bool = False
) -> MoveResult:
    """
    Move a single folder from source to destination.

    Handles:
    - Missing source (skips with SKIPPED_MISSING status)
    - Permission errors
    - Cross-volume moves (via shutil.move copy+delete)
    - Long paths on Windows

    Args:
        src_path: Source folder path
        dest_path: Destination folder path
        dry_run: If True, simulate the move without performing it

    Returns:
        MoveResult with status and details
    """
    src_path = Path(src_path)
    dest_path = Path(dest_path)

    # Extract case_id from the context (we'll use folder name as fallback)
    folder_name = src_path.name

    # Check if source exists
    if not src_path.exists():
        logger.info(f"Source missing (already moved?): {src_path}")
        return MoveResult(
            case_id="",  # Will be set by caller
            source_path=str(src_path),
            dest_path=None,
            status=MoveStatus.SKIPPED_MISSING,
            message="Source folder no longer exists (may have been moved already)"
        )

    # Check if source is a directory
    if not src_path.is_dir():
        logger.error(f"Source is not a directory: {src_path}")
        return MoveResult(
            case_id="",
            source_path=str(src_path),
            dest_path=None,
            status=MoveStatus.ERROR,
            message="Source path is not a directory"
        )

    # Check if destination already exists
    if dest_path.exists():
        logger.warning(f"Destination already exists: {dest_path}")
        return MoveResult(
            case_id="",
            source_path=str(src_path),
            dest_path=str(dest_path),
            status=MoveStatus.SKIPPED_EXISTS,
            message="Destination already exists"
        )

    # Dry run - just report what would happen
    if dry_run:
        logger.info(f"[DRY RUN] {src_path} -> {dest_path}")
        return MoveResult(
            case_id="",
            source_path=str(src_path),
            dest_path=str(dest_path),
            status=MoveStatus.DRY_RUN,
            message=f"Would move to {dest_path}"
        )

    # Perform the actual move
    try:
        # Ensure destination parent exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Use shutil.move which handles cross-volume moves
        logger.info(f"Moving: {src_path} -> {dest_path}")
        shutil.move(str(src_path), str(dest_path))

        return MoveResult(
            case_id="",
            source_path=str(src_path),
            dest_path=str(dest_path),
            status=MoveStatus.SUCCESS,
            message="Moved successfully"
        )

    except PermissionError as e:
        logger.error(f"Permission denied moving {src_path}: {e}")
        return MoveResult(
            case_id="",
            source_path=str(src_path),
            dest_path=str(dest_path),
            status=MoveStatus.ERROR,
            message=f"Permission denied: {e}"
        )

    except OSError as e:
        # Catch various OS errors: path too long, file locked, etc.
        error_msg = str(e)

        # Provide more helpful messages for common errors
        if "WinError 206" in error_msg or "name too long" in error_msg.lower():
            error_msg = f"Path too long: {e}"
        elif "WinError 32" in error_msg or "being used" in error_msg.lower():
            error_msg = f"File/folder is locked or in use: {e}"

        logger.error(f"OS error moving {src_path}: {error_msg}")
        return MoveResult(
            case_id="",
            source_path=str(src_path),
            dest_path=str(dest_path),
            status=MoveStatus.ERROR,
            message=error_msg
        )

    except Exception as e:
        logger.error(f"Unexpected error moving {src_path}: {e}")
        return MoveResult(
            case_id="",
            source_path=str(src_path),
            dest_path=str(dest_path),
            status=MoveStatus.ERROR,
            message=f"Unexpected error: {e}"
        )


class FolderMover:
    """
    Handles moving folders from source locations to destination root.

    Supports dry-run mode for previewing operations and handles
    naming collisions by appending numeric suffixes.
    """

    def __init__(
        self,
        dest_root: Union[str, Path],
        dry_run: bool = False,
        max_moves: Optional[int] = None
    ):
        """
        Initialize the mover with destination settings.

        Args:
            dest_root: The destination root directory
            dry_run: If True, simulate moves without actually performing them
            max_moves: Optional limit on number of moves (for safety testing)
        """
        self.dest_root = Path(dest_root)
        self.dry_run = dry_run
        self.max_moves = max_moves

        # Track names we've claimed during this session
        # (prevents collisions between moves in the same batch)
        self._claimed_names: Set[str] = set()

        # Statistics
        self._stats: Dict[MoveStatus, int] = {status: 0 for status in MoveStatus}

    def move_folder(self, match: FolderMatch) -> MoveResult:
        """
        Move a matched folder to the destination root.

        Handles collisions by appending _1, _2, etc. to folder names.
        Tracks claimed names to prevent collisions within a batch.

        Args:
            match: The FolderMatch describing the folder to move

        Returns:
            MoveResult describing the outcome of the operation
        """
        src_path = Path(match.source_path)
        folder_name = match.folder_name

        # Check if source exists before resolving destination
        if not src_path.exists():
            result = MoveResult(
                case_id=match.case_id,
                source_path=match.source_path,
                dest_path=None,
                status=MoveStatus.SKIPPED_MISSING,
                message="Source folder no longer exists (may have been moved already)"
            )
            self._stats[result.status] += 1
            return result

        # Resolve unique destination path
        dest_path = resolve_destination(
            self.dest_root,
            folder_name,
            self._claimed_names
        )

        # Claim this name for the session
        dest_name = Path(dest_path).name
        self._claimed_names.add(dest_name)

        # Perform the move
        result = move_folder(src_path, dest_path, self.dry_run)

        # Determine if this was a rename (dest name differs from original folder name)
        was_renamed = dest_name != folder_name

        # Adjust status based on rename
        if result.status == MoveStatus.SUCCESS and was_renamed:
            status = MoveStatus.SUCCESS_RENAMED
            message = f"Moved successfully (renamed from {folder_name} to {dest_name})"
        elif result.status == MoveStatus.DRY_RUN and was_renamed:
            status = MoveStatus.DRY_RUN_RENAMED
            message = f"Would move to {dest_path} (renamed from {folder_name} to {dest_name})"
        else:
            status = result.status
            message = result.message

        # Create final result with case_id
        final_result = MoveResult(
            case_id=match.case_id,
            source_path=result.source_path,
            dest_path=result.dest_path,
            status=status,
            message=message
        )

        self._stats[final_result.status] += 1
        return final_result

    def move_all(
        self,
        matches: List[FolderMatch],
        progress_callback=None
    ) -> List[MoveResult]:
        """
        Move all matched folders to the destination root.

        Args:
            matches: List of FolderMatch objects to process
            progress_callback: Optional callable(current, total, match) for progress

        Returns:
            List of MoveResult objects describing each operation
        """
        results: List[MoveResult] = []
        total = len(matches)

        # Apply max_moves limit if set
        if self.max_moves is not None and total > self.max_moves:
            logger.warning(
                f"Limiting moves to {self.max_moves} of {total} "
                f"(--max-moves safety limit)"
            )
            matches = matches[:self.max_moves]
            total = len(matches)

        logger.info(f"Processing {total} folder matches...")

        for i, match in enumerate(matches):
            if progress_callback:
                progress_callback(i + 1, total, match)

            result = self.move_folder(match)
            results.append(result)

            # Log progress every 100 moves
            if (i + 1) % 100 == 0:
                logger.info(f"Processed {i + 1}/{total} folders...")

        logger.info(f"Completed processing {total} folders")
        return results

    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about move operations.

        Returns:
            Dictionary mapping status names to counts
        """
        return {status.value: count for status, count in self._stats.items()}

    def get_summary(self) -> str:
        """
        Get a human-readable summary of move operations.

        Returns:
            Formatted summary string
        """
        stats = self.get_stats()
        total = sum(stats.values())

        lines = [f"Move Summary ({total} total):"]

        # Group by success/skip/error
        success_count = stats.get("success", 0) + stats.get("success_renamed", 0)
        dry_run_count = stats.get("dry_run", 0) + stats.get("dry_run_renamed", 0)
        skipped_count = (
            stats.get("skipped_missing", 0) + stats.get("skipped_exists", 0)
        )
        error_count = stats.get("error", 0)

        if self.dry_run:
            lines.append(f"  Would move: {dry_run_count}")
            if stats.get("dry_run_renamed", 0):
                lines.append(
                    f"    (with rename: {stats.get('dry_run_renamed', 0)})"
                )
        else:
            lines.append(f"  Moved: {success_count}")
            if stats.get("success_renamed", 0):
                lines.append(
                    f"    (with rename: {stats.get('success_renamed', 0)})"
                )

        if skipped_count:
            lines.append(f"  Skipped: {skipped_count}")
            if stats.get("skipped_missing", 0):
                lines.append(
                    f"    (source missing: {stats.get('skipped_missing', 0)})"
                )
            if stats.get("skipped_exists", 0):
                lines.append(
                    f"    (already exists: {stats.get('skipped_exists', 0)})"
                )

        if error_count:
            lines.append(f"  Errors: {error_count}")

        return "\n".join(lines)

    def reset_stats(self) -> None:
        """Reset statistics and claimed names for a new batch."""
        self._stats = {status: 0 for status in MoveStatus}
        self._claimed_names.clear()
