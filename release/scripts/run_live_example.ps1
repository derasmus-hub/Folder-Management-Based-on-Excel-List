#Requires -Version 5.1
<#
.SYNOPSIS
    Live migration example for Folder Mover - actually moves folders.

.DESCRIPTION
    This script demonstrates the recommended live migration workflow.
    IMPORTANT: Always run a dry-run first before using this script!

.NOTES
    This script will MOVE folders. Ensure you have:
    1. Run a dry-run and reviewed the report
    2. Tested with --max-moves 1 first
    3. Verified backup/recovery procedures
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
$ReportPath = "C:\Data\Reports\migration_$(Get-Date -Format 'yyyyMMdd_HHmmss').csv"

# SAFETY LIMIT: Maximum folders to move (set to $null for unlimited)
# Start with 1, then 10, then 100, then $null for full run
$MaxMoves = 1

# Optional: Resume from a previous report (set to $null if not resuming)
$ResumeFromReport = $null
# $ResumeFromReport = "C:\Data\Reports\previous_run.csv"

# Optional: Patterns to exclude (add more as needed)
$ExcludePatterns = @(
    # "*.tmp"
    # "*_backup"
    # "Archive_*"
)

# Behavior when destination exists: "rename" (add _1, _2) or "skip"
$OnDestExists = "rename"

# ============================================================================
# SAFETY CHECKS
# ============================================================================

Write-Host "=" * 60 -ForegroundColor Red
Write-Host "Folder Mover - LIVE MODE (Folders will be MOVED)" -ForegroundColor Red
Write-Host "=" * 60 -ForegroundColor Red
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

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Excel File:   $ExcelFile"
Write-Host "  Source Root:  $SourceRoot"
Write-Host "  Dest Root:    $DestRoot"
Write-Host "  Report:       $ReportPath"
if ($MaxMoves) {
    Write-Host "  Max Moves:    $MaxMoves (SAFETY LIMIT)" -ForegroundColor Yellow
} else {
    Write-Host "  Max Moves:    UNLIMITED" -ForegroundColor Red
}
if ($ResumeFromReport) {
    Write-Host "  Resuming:     $ResumeFromReport" -ForegroundColor Cyan
}
Write-Host ""

# Ensure report directory exists
$ReportDir = Split-Path $ReportPath -Parent
if ($ReportDir -and -not (Test-Path $ReportDir)) {
    New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null
}

# ============================================================================
# CONFIRMATION
# ============================================================================

Write-Host "!" * 60 -ForegroundColor Red
Write-Host "WARNING: This will MOVE folders from:" -ForegroundColor Red
Write-Host "  $SourceRoot" -ForegroundColor White
Write-Host "TO:" -ForegroundColor Red
Write-Host "  $DestRoot" -ForegroundColor White
Write-Host "!" * 60 -ForegroundColor Red
Write-Host ""

$confirmation = Read-Host "Type 'MOVE' to proceed, or anything else to cancel"
if ($confirmation -ne "MOVE") {
    Write-Host "Operation cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""

# ============================================================================
# SCRIPT EXECUTION
# ============================================================================

# Build command arguments
$Args = @(
    "-m", "folder_mover",
    $ExcelFile,
    $SourceRoot,
    $DestRoot,
    "--yes",  # Skip internal confirmation (we already confirmed above)
    "--report", $ReportPath,
    "--on-dest-exists", $OnDestExists,
    "-v"
)

# Add max moves limit
if ($MaxMoves) {
    $Args += "--max-moves"
    $Args += $MaxMoves
}

# Add resume report
if ($ResumeFromReport -and (Test-Path $ResumeFromReport)) {
    $Args += "--resume-from-report"
    $Args += $ResumeFromReport
}

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
    Write-Host "Migration completed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Report saved to: $ReportPath" -ForegroundColor Cyan
    Write-Host ""
    if ($MaxMoves) {
        Write-Host "Next steps:" -ForegroundColor Yellow
        Write-Host "  1. Review the report to verify moves were correct"
        Write-Host "  2. Increase MaxMoves (e.g., 10, 100) and run again"
        Write-Host "  3. When confident, set MaxMoves = `$null for full run"
        Write-Host "  4. Use --resume-from-report to continue where you left off"
    }
} elseif ($exitCode -eq 2) {
    Write-Host "Migration completed with some errors (exit code: 2)" -ForegroundColor Yellow
    Write-Host "Review the report for ERROR entries: $ReportPath"
    Write-Host ""
    Write-Host "To resume, set:" -ForegroundColor Yellow
    Write-Host "  `$ResumeFromReport = `"$ReportPath`""
} else {
    Write-Host "Migration failed (exit code: $exitCode)" -ForegroundColor Red
    Write-Host "Review the output above for details."
}

Write-Host "=" * 60 -ForegroundColor Cyan
