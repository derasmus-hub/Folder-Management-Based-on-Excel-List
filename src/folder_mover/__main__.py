"""
Entry point for running the package as a module.

Usage: python -m folder_mover [arguments]
"""

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
