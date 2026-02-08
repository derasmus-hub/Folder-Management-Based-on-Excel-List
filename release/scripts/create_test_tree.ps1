#Requires -Version 5.1
<#
.SYNOPSIS
    Creates a test folder structure and Excel file for testing Folder Mover.

.DESCRIPTION
    This script creates a sample directory tree and Excel file with CaseIDs
    to help you test the folder mover before using it on production data.

.PARAMETER TestRoot
    Root directory where test folders will be created. Default: .\test_environment

.EXAMPLE
    .\create_test_tree.ps1
    Creates test environment in .\test_environment

.EXAMPLE
    .\create_test_tree.ps1 -TestRoot "C:\Temp\FolderMoverTest"
    Creates test environment in specified directory
#>

param(
    [string]$TestRoot = ".\test_environment"
)

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Creating Test Environment for Folder Mover" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Create base directories
$SourceRoot = Join-Path $TestRoot "source"
$DestRoot = Join-Path $TestRoot "dest"
$ReportsDir = Join-Path $TestRoot "reports"

Write-Host "Creating directory structure..." -ForegroundColor Yellow
Write-Host "  Test Root:    $TestRoot"
Write-Host "  Source:       $SourceRoot"
Write-Host "  Destination:  $DestRoot"
Write-Host "  Reports:      $ReportsDir"
Write-Host ""

New-Item -ItemType Directory -Path $SourceRoot -Force | Out-Null
New-Item -ItemType Directory -Path $DestRoot -Force | Out-Null
New-Item -ItemType Directory -Path $ReportsDir -Force | Out-Null

# Create test folders with various naming patterns
$testFolders = @(
    # Standard case folders
    @{ Path = "Case_00123_Smith"; CaseID = "00123" },
    @{ Path = "Case_00456_Jones"; CaseID = "00456" },
    @{ Path = "Case_00789_Williams"; CaseID = "00789" },

    # Nested folders
    @{ Path = "2023\Archive\Case_01111_Brown"; CaseID = "01111" },
    @{ Path = "2024\Active\Case_02222_Davis"; CaseID = "02222" },

    # Different naming conventions
    @{ Path = "CASE-03333-Miller"; CaseID = "03333" },
    @{ Path = "03333_SecondMatch"; CaseID = "03333" },  # Duplicate CaseID

    # Special characters (Windows-safe)
    @{ Path = "Case #04444 (2024)"; CaseID = "04444" },

    # Folders that should NOT be moved (not in CaseID list)
    @{ Path = "Unrelated_Folder"; CaseID = $null },
    @{ Path = "Archive\Old_Data"; CaseID = $null },

    # Folders to test exclusion patterns
    @{ Path = "Case_05555_temp"; CaseID = "05555" },
    @{ Path = "backup.bak"; CaseID = $null }
)

Write-Host "Creating test folders..." -ForegroundColor Yellow

$caseIDs = @()
foreach ($folder in $testFolders) {
    $folderPath = Join-Path $SourceRoot $folder.Path
    New-Item -ItemType Directory -Path $folderPath -Force | Out-Null

    # Create a sample file in each folder
    $sampleFile = Join-Path $folderPath "sample_document.txt"
    "This is a sample file in folder: $($folder.Path)`nCreated: $(Get-Date)" | Out-File $sampleFile -Encoding UTF8

    Write-Host "  Created: $($folder.Path)" -ForegroundColor Gray

    if ($folder.CaseID) {
        $caseIDs += $folder.CaseID
    }
}

# Add some CaseIDs that won't have matches (NOT_FOUND testing)
$caseIDs += "99999"
$caseIDs += "88888"

# Remove duplicates and sort
$caseIDs = $caseIDs | Sort-Object -Unique

Write-Host ""
Write-Host "Creating Excel file with CaseIDs..." -ForegroundColor Yellow

# Create Excel file using COM object if available, otherwise create CSV
$excelPath = Join-Path $TestRoot "test_cases.xlsx"
$csvPath = Join-Path $TestRoot "test_cases.csv"

try {
    # Try to create Excel file
    $excel = New-Object -ComObject Excel.Application -ErrorAction Stop
    $excel.Visible = $false
    $excel.DisplayAlerts = $false

    $workbook = $excel.Workbooks.Add()
    $worksheet = $workbook.Worksheets.Item(1)
    $worksheet.Name = "CaseIDs"

    # Add header
    $worksheet.Cells.Item(1, 1) = "CaseID"

    # Add CaseIDs
    $row = 2
    foreach ($caseID in $caseIDs) {
        $worksheet.Cells.Item($row, 1) = $caseID
        $row++
    }

    # Auto-fit column
    $worksheet.Columns.Item(1).AutoFit() | Out-Null

    # Save and close
    $workbook.SaveAs($excelPath, 51)  # 51 = xlsx format
    $workbook.Close()
    $excel.Quit()

    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($worksheet) | Out-Null
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($workbook) | Out-Null
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()

    Write-Host "  Created: $excelPath" -ForegroundColor Green
    $useExcel = $true
}
catch {
    Write-Host "  Excel not available, creating CSV instead..." -ForegroundColor Yellow

    # Create CSV as fallback
    $caseIDs | ForEach-Object { [PSCustomObject]@{ CaseID = $_ } } |
        Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8

    Write-Host "  Created: $csvPath" -ForegroundColor Green
    Write-Host ""
    Write-Host "  NOTE: To use the tool, you'll need to convert this CSV to XLSX" -ForegroundColor Yellow
    Write-Host "        or install openpyxl and modify the tool to read CSV." -ForegroundColor Yellow
    $useExcel = $false
}

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Green
Write-Host "Test Environment Created Successfully!" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Green
Write-Host ""
Write-Host "Test CaseIDs:" -ForegroundColor Yellow
foreach ($id in $caseIDs) {
    $hasMatch = $testFolders | Where-Object { $_.CaseID -eq $id }
    if ($hasMatch) {
        $matchCount = ($hasMatch | Measure-Object).Count
        if ($matchCount -gt 1) {
            Write-Host "  $id - $matchCount matches (MULTIPLE_MATCHES)" -ForegroundColor Cyan
        } else {
            Write-Host "  $id - 1 match" -ForegroundColor Gray
        }
    } else {
        Write-Host "  $id - no match (NOT_FOUND)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "To test the folder mover:" -ForegroundColor Yellow
Write-Host ""

if ($useExcel) {
    $dataFile = $excelPath
} else {
    $dataFile = $csvPath
    Write-Host "  (Convert $csvPath to .xlsx first)" -ForegroundColor Yellow
}

Write-Host "  # 1. Dry run:" -ForegroundColor Cyan
Write-Host "  python -m folder_mover `"$dataFile`" `"$SourceRoot`" `"$DestRoot`" --dry-run --report `"$ReportsDir\dryrun.csv`""
Write-Host ""
Write-Host "  # 2. Move one folder:" -ForegroundColor Cyan
Write-Host "  python -m folder_mover `"$dataFile`" `"$SourceRoot`" `"$DestRoot`" --max-moves 1 --report `"$ReportsDir\move1.csv`""
Write-Host ""
Write-Host "  # 3. Full migration:" -ForegroundColor Cyan
Write-Host "  python -m folder_mover `"$dataFile`" `"$SourceRoot`" `"$DestRoot`" --report `"$ReportsDir\full.csv`""
Write-Host ""
Write-Host "  # 4. With exclusions:" -ForegroundColor Cyan
Write-Host "  python -m folder_mover `"$dataFile`" `"$SourceRoot`" `"$DestRoot`" --exclude-pattern `"*temp*`" --dry-run"
Write-Host ""
