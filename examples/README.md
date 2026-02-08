# Examples

This directory contains example files for the Folder Mover tool.

## Files

### sample_report.csv

A sample CSV report showing various status types:

| Status | Count | Description |
|--------|-------|-------------|
| MOVED | 1 | Successfully moved folder |
| MOVED_RENAMED | 1 | Moved with suffix due to name collision |
| MULTIPLE_MATCHES | 2 | CaseID 00789 matched 2 folders (both moved) |
| SKIPPED_MISSING | 1 | Source folder no longer exists |
| SKIPPED_EXISTS | 1 | Destination folder already exists |
| NOT_FOUND | 2 | CaseIDs with no matching folders |
| ERROR | 1 | Failed due to permission error |

### sample_caselist.xlsx

A sample Excel file with CaseIDs in Column A. To create your own:

1. Open Excel
2. Enter CaseIDs in Column A (one per row)
3. Save as `.xlsx` format

Example content:
```
A1: 00123
A2: 00456
A3: 00789
A4: 00111
A5: 00222
A6: 00333
A7: 99999
A8: 88888
```

## Creating a Test Environment

```bash
# Create test directories
mkdir -p test_source/Case_00123_Smith
mkdir -p test_source/Case_00456_Jones
mkdir -p test_source/2023/Case_00789_Active
mkdir -p test_source/2024/Case_00789_Renewed
mkdir -p test_dest

# Create test Excel file with CaseIDs
# (use Excel or openpyxl to create sample_caselist.xlsx)

# Run dry-run first
python -m folder_mover sample_caselist.xlsx test_source test_dest --dry-run

# Then run with max-moves limit
python -m folder_mover sample_caselist.xlsx test_source test_dest --max-moves 1
```
