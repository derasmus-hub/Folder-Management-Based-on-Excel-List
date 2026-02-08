#Requires -Version 5.1
<#
.SYNOPSIS
    Dry-run example for Folder Mover - previews moves without making changes.

.DESCRIPTION
    This script demonstrates the recommended dry-run workflow.
    Customize the variables below for your environment.

.NOTES
    Always run a dry-run first before any live operation!
#>

# ============================================================================
# CONFIGURATION - Edit these variables for your environment
# ============================================================================

# Path to Excel file with CaseIDs in Column A
$ExcelFile = "C:\Data\CaseList.xlsx"

# Source directory to scan for folders
$SourceRoot = "C:\Data\SourceFolders"

# Destination directory where matched folders will be moved
$DestRoot = "C:\Data\DestinationFolders"

# Report file path (auto-generated name if empty)
$ReportPath = "C:\Data\Reports\dryrun_$(Get-Date -Format 'yyyyMMdd_HHmmss').csv"

# Optional: Patterns to exclude (add more as needed)
$ExcludePatterns = @(
    # "*.tmp"
    # "*_backup"
    # "Archive_*"
)

# ============================================================================
# SCRIPT EXECUTION
# ============================================================================

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Folder Mover - DRY RUN (No changes will be made)" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Excel File:   $ExcelFile"
Write-Host "  Source Root:  $SourceRoot"
Write-Host "  Dest Root:    $DestRoot"
Write-Host "  Report:       $ReportPath"
Write-Host ""

# Validate paths exist
if (-not (Test-Path $ExcelFile)) {
    Write-Host "ERROR: Excel file not found: $ExcelFile" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $SourceRoot)) {
    Write-Host "ERROR: Source root not found: $SourceRoot" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $DestRoot)) {
    Write-Host "WARNING: Dest root does not exist: $DestRoot" -ForegroundColor Yellow
    Write-Host "Creating destination directory..."
    New-Item -ItemType Directory -Path $DestRoot -Force | Out-Null
}

# Ensure report directory exists
$ReportDir = Split-Path $ReportPath -Parent
if ($ReportDir -and -not (Test-Path $ReportDir)) {
    New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null
}

# Build command arguments
$Args = @(
    "-m", "folder_mover",
    $ExcelFile,
    $SourceRoot,
    $DestRoot,
    "--dry-run",
    "--report", $ReportPath,
    "-v"
)

# Add exclusion patterns
foreach ($pattern in $ExcludePatterns) {
    if ($pattern) {
        $Args += "--exclude-pattern"
        $Args += $pattern
    }
}

Write-Host "Running command:" -ForegroundColor Yellow
Write-Host "  python $($Args -join ' ')" -ForegroundColor Gray
Write-Host ""

# Run the command
python @Args

$exitCode = $LASTEXITCODE

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan

if ($exitCode -eq 0) {
    Write-Host "Dry run completed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Review the report: $ReportPath"
    Write-Host "  2. Check for NOT_FOUND entries (CaseIDs with no matches)"
    Write-Host "  3. If satisfied, run with --max-moves 1 to test a single move"
    Write-Host "  4. Then run without --dry-run for full migration"
} else {
    Write-Host "Dry run completed with errors (exit code: $exitCode)" -ForegroundColor Red
    Write-Host "Review the output above and the report for details."
}

Write-Host "=" * 60 -ForegroundColor Cyan
