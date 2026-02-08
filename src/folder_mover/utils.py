r"""
Windows path utilities for handling long paths and UNC paths.

This module provides:
- normalize_path(): Normalize paths to absolute form, preserving UNC
- to_extended_length_path(): Convert to \\?\ form for Windows API calls
- from_extended_length_path(): Convert back to normal form for display
- safe_move(): Robust folder move with fallback for cross-volume moves
"""

import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Tuple, Union

logger = logging.getLogger(__name__)

# Windows extended-length path prefixes
EXTENDED_PATH_PREFIX = "\\\\?\\"
EXTENDED_UNC_PREFIX = "\\\\?\\UNC\\"
UNC_PREFIX = "\\\\"


def normalize_path(path: Union[str, Path]) -> str:
    """
    Normalize a path to absolute form, preserving UNC paths.

    This function:
    - Converts Path objects to strings
    - Resolves relative paths to absolute
    - Preserves UNC paths (\\\\server\\share) without breaking them
    - Normalizes path separators
    - Does NOT add extended-length prefix (use to_extended_length_path for that)

    Args:
        path: A file path as string or Path object

    Returns:
        Normalized absolute path as string

    Examples:
        >>> normalize_path("relative/path")
        'C:\\\\current\\\\dir\\\\relative\\\\path'
        >>> normalize_path("\\\\\\\\server\\\\share\\\\folder")
        '\\\\\\\\server\\\\share\\\\folder'
        >>> normalize_path("C:/Users/test")
        'C:\\\\Users\\\\test'
    """
    path_str = str(path)

    # Check if it's already an extended-length path
    if path_str.startswith(EXTENDED_PATH_PREFIX):
        # Already extended, just return normalized
        return path_str

    # Check if it's a UNC path
    is_unc = path_str.startswith(UNC_PREFIX) and not path_str.startswith(EXTENDED_PATH_PREFIX)

    if is_unc:
        # For UNC paths, we can't use Path.resolve() directly as it may break
        # Instead, normalize the path components
        # Remove the leading \\\\ and split
        unc_part = path_str[2:]  # Remove leading \\
        parts = unc_part.replace("/", "\\").split("\\")

        # Filter empty parts (from double slashes) but keep structure
        cleaned_parts = []
        for i, part in enumerate(parts):
            if part or i < 2:  # Keep server and share even if parsing issues
                cleaned_parts.append(part)

        # Reconstruct UNC path
        normalized = UNC_PREFIX + "\\".join(cleaned_parts)
        return normalized

    # For local paths, use Path.resolve() for full normalization
    try:
        resolved = Path(path_str).resolve()
        return str(resolved)
    except (OSError, ValueError):
        # If resolve fails, do basic normalization
        return os.path.abspath(os.path.normpath(path_str))


def to_extended_length_path(path: Union[str, Path]) -> str:
    """
    Convert a path to Windows extended-length form (\\\\?\\ prefix).

    Extended-length paths allow Windows API to handle paths longer than
    MAX_PATH (260 characters). This function:
    - Adds \\\\?\\ prefix for local paths (C:\\...)
    - Adds \\\\?\\UNC\\ prefix for UNC paths (\\\\server\\share)
    - Returns path unchanged on non-Windows platforms
    - Returns path unchanged if already in extended form

    Args:
        path: A file path as string or Path object

    Returns:
        Path with extended-length prefix on Windows, unchanged otherwise

    Examples:
        >>> to_extended_length_path("C:\\\\Users\\\\test")  # Windows
        '\\\\\\\\?\\\\C:\\\\Users\\\\test'
        >>> to_extended_length_path("\\\\\\\\server\\\\share")  # Windows UNC
        '\\\\\\\\?\\\\UNC\\\\server\\\\share'
    """
    if sys.platform != "win32":
        return str(path)

    path_str = normalize_path(path)

    # Already extended?
    if path_str.startswith(EXTENDED_PATH_PREFIX):
        return path_str

    # UNC path?
    if path_str.startswith(UNC_PREFIX):
        # \\server\share -> \\?\UNC\server\share
        return EXTENDED_UNC_PREFIX + path_str[2:]

    # Local path with drive letter?
    if len(path_str) >= 2 and path_str[1] == ":":
        return EXTENDED_PATH_PREFIX + path_str

    # Relative or other path - normalize first
    try:
        abs_path = str(Path(path_str).resolve())
        if abs_path.startswith(UNC_PREFIX):
            return EXTENDED_UNC_PREFIX + abs_path[2:]
        return EXTENDED_PATH_PREFIX + abs_path
    except (OSError, ValueError):
        # Can't resolve, return as-is
        return path_str


def from_extended_length_path(path: Union[str, Path]) -> str:
    """
    Convert an extended-length path back to normal form for display.

    This function:
    - Removes \\\\?\\ prefix from local paths
    - Converts \\\\?\\UNC\\server\\share back to \\\\server\\share
    - Returns path unchanged if not in extended form

    Args:
        path: A file path that may be in extended-length form

    Returns:
        Path in normal human-readable form

    Examples:
        >>> from_extended_length_path("\\\\\\\\?\\\\C:\\\\Users\\\\test")
        'C:\\\\Users\\\\test'
        >>> from_extended_length_path("\\\\\\\\?\\\\UNC\\\\server\\\\share")
        '\\\\\\\\server\\\\share'
    """
    path_str = str(path)

    # Extended UNC path?
    if path_str.startswith(EXTENDED_UNC_PREFIX):
        # \\?\UNC\server\share -> \\server\share
        return UNC_PREFIX + path_str[len(EXTENDED_UNC_PREFIX):]

    # Extended local path?
    if path_str.startswith(EXTENDED_PATH_PREFIX):
        # \\?\C:\path -> C:\path
        return path_str[len(EXTENDED_PATH_PREFIX):]

    return path_str


def is_unc_path(path: Union[str, Path]) -> bool:
    """
    Check if a path is a UNC path (network share).

    Args:
        path: Path to check

    Returns:
        True if path is UNC (\\\\server\\share or \\\\?\\UNC\\...)
    """
    path_str = str(path)

    # Extended UNC path: \\?\UNC\server\share
    if path_str.startswith(EXTENDED_UNC_PREFIX):
        return True

    # Extended local path: \\?\C:\ - NOT a UNC path
    if path_str.startswith(EXTENDED_PATH_PREFIX):
        return False

    # Normal UNC path: \\server\share (but not \\?\)
    if path_str.startswith(UNC_PREFIX):
        return True

    return False


def safe_move(
    src: Union[str, Path],
    dest: Union[str, Path],
    use_extended_paths: bool = True
) -> Tuple[bool, str]:
    """
    Safely move a folder, handling cross-volume moves and Windows errors.

    This function:
    - Uses extended-length paths on Windows for long path support
    - Handles cross-volume moves (copy + delete)
    - Falls back to shutil.copytree + shutil.rmtree if shutil.move fails
    - Provides clear error messages for common Windows errors

    Args:
        src: Source folder path
        dest: Destination folder path
        use_extended_paths: Whether to use \\\\?\\ prefix on Windows

    Returns:
        Tuple of (success: bool, message: str)
        On success: (True, "Moved successfully")
        On failure: (False, "Error description")

    Raises:
        Nothing - all errors are caught and returned as (False, message)
    """
    src_str = str(src)
    dest_str = str(dest)

    # Convert to extended paths on Windows if requested
    if sys.platform == "win32" and use_extended_paths:
        src_extended = to_extended_length_path(src_str)
        dest_extended = to_extended_length_path(dest_str)
    else:
        src_extended = src_str
        dest_extended = dest_str

    try:
        # Try standard move first (handles same-volume efficiently)
        shutil.move(src_extended, dest_extended)
        return (True, "Moved successfully")

    except shutil.Error as e:
        # shutil.move can raise this for various reasons
        error_msg = str(e)
        logger.warning(f"shutil.move failed, attempting copy+delete: {e}")

        # Fall back to copy + delete
        return _copy_and_delete(src_extended, dest_extended, error_msg)

    except PermissionError as e:
        # WinError 5: Access denied
        return (False, f"PermissionError: {_format_windows_error(e)}")

    except OSError as e:
        error_code = getattr(e, "winerror", None)

        # Check for specific Windows errors
        if error_code == 32:
            # WinError 32: File in use
            return (False, f"File/folder is locked or in use: {_format_windows_error(e)}")

        elif error_code == 5:
            # WinError 5: Access denied
            return (False, f"Access denied: {_format_windows_error(e)}")

        elif error_code == 206:
            # WinError 206: Path too long (even with \\?\)
            return (False, f"Path too long: {_format_windows_error(e)}")

        elif error_code == 17:
            # WinError 17: Can't move to different drive
            # Fall back to copy + delete
            logger.info("Cross-volume move detected, using copy+delete")
            return _copy_and_delete(src_extended, dest_extended, str(e))

        elif error_code in (64, 121, 1231):
            # Network errors - worth noting specifically
            # 64: Network name no longer available
            # 121: Semaphore timeout
            # 1231: Network location cannot be reached
            return (False, f"Network error: {_format_windows_error(e)}")

        else:
            # Other OS error
            return (False, f"OSError: {_format_windows_error(e)}")

    except Exception as e:
        return (False, f"Unexpected error: {type(e).__name__}: {e}")


def _copy_and_delete(
    src: str,
    dest: str,
    original_error: str
) -> Tuple[bool, str]:
    """
    Fall back to copy + delete when move fails.

    Args:
        src: Source path (may be extended-length)
        dest: Destination path (may be extended-length)
        original_error: The error that caused the fallback

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Copy the entire tree
        shutil.copytree(src, dest)

        # Verify copy succeeded before deleting source
        if os.path.exists(dest):
            # Delete source
            shutil.rmtree(src)
            logger.info(f"Moved via copy+delete fallback")
            return (True, "Moved successfully (via copy+delete)")
        else:
            return (False, f"Copy appeared to succeed but destination not found")

    except PermissionError as e:
        # Clean up partial copy if possible
        _cleanup_partial_copy(dest)
        return (False, f"PermissionError during copy: {_format_windows_error(e)}")

    except OSError as e:
        _cleanup_partial_copy(dest)
        return (False, f"OSError during copy: {_format_windows_error(e)}")

    except Exception as e:
        _cleanup_partial_copy(dest)
        return (False, f"Error during copy+delete fallback: {type(e).__name__}: {e}")


def _cleanup_partial_copy(dest: str) -> None:
    """Attempt to clean up a partial copy on failure."""
    try:
        if os.path.exists(dest):
            shutil.rmtree(dest)
            logger.debug(f"Cleaned up partial copy at {dest}")
    except Exception as e:
        logger.warning(f"Could not clean up partial copy at {dest}: {e}")


def _format_windows_error(e: Exception) -> str:
    """
    Format a Windows error with its error code if available.

    Args:
        e: The exception to format

    Returns:
        Formatted error string
    """
    error_code = getattr(e, "winerror", None)
    if error_code is not None:
        return f"[WinError {error_code}] {e}"
    return str(e)
