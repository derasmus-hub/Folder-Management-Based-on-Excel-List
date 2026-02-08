# Folder Mover

A Windows-focused Python CLI tool for moving folders based on CaseIDs from an Excel file.

## Overview

This tool scans a source directory tree for folders whose names contain CaseIDs listed in an Excel file (Column A). Matched folders are moved directly into a destination directory. The tool handles naming collisions, supports dry-run mode for previewing operations, and generates detailed CSV reports.

### Features

- **Excel-driven**: Reads CaseIDs from Column A of an XLSX file
- **Leading zero preservation**: CaseIDs are treated as strings to preserve leading zeros
- **Substring matching**: A folder matches if its name contains the CaseID
- **Flat destination**: Folders are moved directly into DestRoot (no source structure preserved)
- **Collision handling**: Name conflicts resolved with `_1`, `_2`, etc. suffixes
- **Dry-run mode**: Preview operations without making changes
- **Idempotent**: Skip folders already at destination
- **Detailed reporting**: CSV report of all operations with timestamps

## Installation

1. Clone or download this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python -m folder_mover <excel_file> <source_root> <dest_root> [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `excel_file` | Path to Excel XLSX file with CaseIDs in Column A |
| `source_root` | Root directory to search for matching folders |
| `dest_root` | Destination directory where matched folders will be moved |

### Options

| Option | Description |
|--------|-------------|
| `-n, --dry-run, --whatif` | Preview operations without actually moving folders |
| `-y, --yes` | Skip confirmation prompt (use with caution) |
| `-r, --report FILE` | Path for CSV report (default: `report_YYYYMMDD_HHMMSS.csv`) |
| `-s, --sheet NAME` | Excel sheet name to read (default: active sheet) |
| `--max-moves N` | Limit to first N move operations (for safe testing) |
| `--max-folders N` | Limit folder scan to first N folders (for testing) |
| `--caseid-limit N` | Only process first N CaseIDs from Excel (for testing) |
| `-v, --verbose` | Increase verbosity (-v for INFO, -vv for DEBUG) |
| `--version` | Show version and exit |
| `-h, --help` | Show help message and exit |

**Note:** In live mode (without `--dry-run`), you will be prompted to confirm before any folders are moved. Use `--yes` to skip this prompt for automated/scripted runs.

### Examples

Basic usage:
```bash
python -m folder_mover caselist.xlsx C:\Data\Source C:\Data\Dest
```

Preview changes without moving:
```bash
python -m folder_mover caselist.xlsx C:\Data\Source C:\Data\Dest --dry-run
```

Verbose output with report:
```bash
python -m folder_mover caselist.xlsx C:\Data\Source C:\Data\Dest -v --report moves.csv
```

Safe test run (move only 1 folder):
```bash
python -m folder_mover caselist.xlsx C:\Data\Source C:\Data\Dest --max-moves 1
```

## Excel File Format

The Excel file (.xlsx) should have CaseIDs in **Column A**:

| Column A |
|----------|
| 00123    |
| 00456    |
| CASE-789 |
| 00123    |

### Important Notes

- **Leading zeros**: CaseIDs are read as strings, so leading zeros like `00123` are preserved exactly
- **Empty cells**: Empty rows are automatically skipped
- **Duplicates**: Duplicate CaseIDs are removed (first occurrence kept)
- **Whitespace**: Leading/trailing whitespace is trimmed
- **Data types**: Numeric values are converted to strings (e.g., `123` becomes `"123"`)
- **Sheet selection**: By default reads the active sheet; use `-s` to specify a sheet name

### Example Excel Structure

```
A1: 00123      <- Preserved as "00123"
A2: CASE-456   <- String with special characters
A3:            <- Empty, skipped
A4: 00123      <- Duplicate, skipped
A5: 789        <- Numeric, becomes "789"
```

Result: `["00123", "CASE-456", "789"]`

## CSV Report Format

When using `--report`, a detailed CSV file is generated with the following columns:

| Column | Description |
|--------|-------------|
| `timestamp` | When the operation occurred (YYYY-MM-DD HH:MM:SS) |
| `case_id` | The CaseID from the Excel file |
| `status` | Operation result (see Status Values below) |
| `source_path` | Original folder location |
| `dest_path` | Destination folder location (if moved) |
| `message` | Details about the operation |

### Status Values

| Status | Description |
|--------|-------------|
| `MOVED` | Folder moved successfully |
| `MOVED_RENAMED` | Moved with suffix (`_1`, `_2`) due to name collision |
| `FOUND_DRYRUN` | Would move (dry-run mode) |
| `FOUND_DRYRUN_RENAMED` | Would move with rename (dry-run mode) |
| `NOT_FOUND` | No folders matched this CaseID |
| `MULTIPLE_MATCHES` | CaseID matched multiple folders (all moved) |
| `SKIPPED_MISSING` | Source folder no longer exists |
| `SKIPPED_EXISTS` | Destination already exists |
| `ERROR` | Operation failed (see message for details) |

### Sample Report Output

```csv
timestamp,case_id,status,source_path,dest_path,message
2024-01-15 10:30:00,00123,MOVED,C:\Source\Case_00123_Smith,C:\Dest\Case_00123_Smith,Moved successfully
2024-01-15 10:30:01,00456,MOVED_RENAMED,C:\Source\Case_00456,C:\Dest\Case_00456_1,Moved successfully (renamed from Case_00456 to Case_00456_1)
2024-01-15 10:30:02,00789,MULTIPLE_MATCHES,C:\Source\2023\Case_00789,C:\Dest\Case_00789,[Multiple matches] Moved successfully
2024-01-15 10:30:02,00789,MULTIPLE_MATCHES,C:\Source\2024\Case_00789,C:\Dest\Case_00789_1,[Multiple matches] Moved successfully
2024-01-15 10:30:03,99999,NOT_FOUND,,,No matching folders found for this CaseID
2024-01-15 10:30:04,00111,ERROR,C:\Source\Case_00111,,PermissionError: Access denied
```

## Safe Test Run

Before running on production data, follow these steps to verify the tool works correctly:

### Step 1: Create a Test Environment

```bash
# Create test directories
mkdir test_source
mkdir test_source\Case_00123_Smith
mkdir test_source\Case_00456_Jones
mkdir test_source\Archive
mkdir test_source\Archive\Case_00789_Old
mkdir test_dest

# Add some files to test folders (optional)
echo "test" > test_source\Case_00123_Smith\document.txt
```

Create a test Excel file (`test_cases.xlsx`) with CaseIDs:
```
A1: 00123
A2: 00456
A3: 00789
A4: 99999  (no match - will show NOT_FOUND)
```

### Step 2: Dry Run First

Always preview what will happen before making changes:

```bash
python -m folder_mover test_cases.xlsx test_source test_dest --dry-run
```

Review the output and generated report to verify:
- Correct folders are matched
- NOT_FOUND CaseIDs are expected
- No unexpected matches

### Step 3: Move One Folder

Test with a single folder to verify the move works:

```bash
python -m folder_mover test_cases.xlsx test_source test_dest --max-moves 1
```

Check:
- The folder was moved to `test_dest`
- The report shows `MOVED` status
- Original location is empty

### Step 4: Run Full Migration

Once verified, run without limits:

```bash
python -m folder_mover caselist.xlsx C:\Data\Source C:\Data\Dest --report migration.csv
```

### Tips for Large Runs

- Use `--max-folders 1000` to test scanning performance first
- Use `--caseid-limit 10` to test with a subset of CaseIDs
- Use `-v` for detailed logging during troubleshooting
- Always generate a report for audit trail

## Project Structure

```
src/folder_mover/
├── __init__.py     # Package metadata
├── __main__.py     # Module entry point
├── cli.py          # Command-line interface
├── excel.py        # Excel file reading
├── indexer.py      # Folder scanning and indexing
├── mover.py        # Folder move operations
├── report.py       # CSV report generation
└── types.py        # Data classes and type definitions

examples/
├── sample_report.csv   # Example CSV report
└── README.md           # Examples documentation
```

## Running Tests

```bash
pip install -r requirements.txt
PYTHONPATH=src pytest tests/ -v
```

## License

MIT License
