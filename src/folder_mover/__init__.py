"""
Folder Mover - A Windows-focused CLI tool for moving folders based on Excel CaseID lists.

This package provides functionality to:
- Read CaseIDs from an Excel XLSX file (Column A)
- Index folders under a source root directory
- Match folders by checking if folder names contain the CaseID
- Move matched folders to a destination root
- Handle naming collisions with numeric suffixes
- Generate detailed CSV reports of operations
"""

__version__ = "0.1.0"
__author__ = "Folder Mover Team"
