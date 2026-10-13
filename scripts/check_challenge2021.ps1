# Checks the Challenge 2021 download in data\challenge2021\training:
#   1. record counts per source against the official totals
#   2. every signal file (.mat) has exactly the size its header (.hea) implies,
#      which catches files that were cut off mid-download
#
# Usage, from the repository root:
#   powershell -ExecutionPolicy Bypass -File scripts\check_challenge2021.ps1
#
# Add -DeleteBad to delete incomplete files, then re-run download_challenge2021.ps1:
#   powershell -ExecutionPolicy Bypass -File scripts\check_challenge2021.ps1 -DeleteBad

param([switch]$DeleteBad)

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$root = 'data\challenge2021\training'
$targets = [ordered]@{ 'georgia' = 10344; 'cpsc_2018' = 6877; 'cpsc_2018_extra' = 3453 }

$running = @(Get-Process -Name wget -ErrorAction SilentlyContinue).Count
Write-Host "wget windows still running: $running"
if ($running -gt 0) {
    Write-Host 'Downloads are still in progress, so the numbers below are provisional.'
}
Write-Host ''

$allOk = ($running -eq 0)
$bad = New-Object System.Collections.Generic.List[string]

foreach ($s in $targets.Keys) {
    $dir = Join-Path $root $s
    $heaFiles = @(Get-ChildItem -Path $dir -Recurse -Filter *.hea -ErrorAction SilentlyContinue)
    $matCount = @(Get-ChildItem -Path $dir -Recurse -Filter *.mat -ErrorAction SilentlyContinue).Count

    foreach ($h in $heaFiles) {
        $mat = [IO.Path]::ChangeExtension($h.FullName, '.mat')
        try {
            $lines = @(Get-Content -Path $h.FullName -TotalCount 2)
            $first = $lines[0].Trim() -split '\s+'
            $nsig = [int]$first[1]
            $nsamp = [int64]$first[3]
            $offset = 24
            if ($lines.Count -gt 1 -and $lines[1] -match '\+(\d+)') { $offset = [int]$Matches[1] }
            $expected = $offset + 2 * $nsig * $nsamp
        }
        catch {
            # Unreadable header: treat the record as incomplete
            $bad.Add($h.FullName)
            if (Test-Path $mat) { $bad.Add($mat) }
            continue
        }
        if (-not (Test-Path $mat)) {
            $bad.Add($mat)
        }
        elseif ((Get-Item $mat).Length -ne $expected) {
            $bad.Add($mat)
        }
    }

    $target = $targets[$s]
    if ($heaFiles.Count -ne $target -or $matCount -ne $target) { $allOk = $false }
    Write-Host ('{0,-16} hea {1,6}   mat {2,6}   target {3,6}' -f $s, $heaFiles.Count, $matCount, $target)
}

Write-Host ''
Write-Host "Missing or incomplete signal files: $($bad.Count)"
$bad | Select-Object -First 20 | ForEach-Object { Write-Host "  $_" }
if ($bad.Count -gt 0) { $allOk = $false }

if ($DeleteBad -and $bad.Count -gt 0) {
    foreach ($b in $bad) {
        if (Test-Path $b) { Remove-Item -Path $b -Force }
    }
    Write-Host 'Deleted the incomplete files. Now run scripts\download_challenge2021.ps1 again.'
}

Write-Host ''
if ($allOk) {
    Write-Host 'RESULT: Challenge 2021 download is COMPLETE and intact.' -ForegroundColor Green
}
else {
    Write-Host 'RESULT: NOT complete yet. Run scripts\download_challenge2021.ps1, wait for its windows to close, then run this check again.' -ForegroundColor Yellow
}
