# Downloads CODE-15% (Brazil) from Zenodo into data\code15: the label file exams.csv
# and the first N of its 18 HDF5 parts (default 4, about 11 GB), then unzips them.
#
# Safe to re-run: finished files are skipped and interrupted downloads resume.
#
# Usage, from the repository root:
#   powershell -ExecutionPolicy Bypass -File scripts\download_code15.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\download_code15.ps1 -Parts 6

param([int]$Parts = 4)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$dest = 'data\code15'
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$base = 'https://zenodo.org/records/4916206/files'

$files = @('exams.csv')
for ($i = 0; $i -lt $Parts; $i++) { $files += "exams_part$i.zip" }

foreach ($f in $files) {
    $out = Join-Path $dest $f
    if (Test-Path $out) {
        Write-Host "Already downloaded: $f"
        continue
    }
    # Download to a .part file and rename only after curl succeeds, so a file with
    # the final name is always complete.
    $partial = $out + '.part'
    $url = '{0}/{1}?download=1' -f $base, $f
    Write-Host "Downloading $f"
    & curl.exe -L -C - --retry 10 --retry-delay 10 -o $partial $url
    if ($LASTEXITCODE -ne 0) {
        throw "Download of $f failed (curl exit code $LASTEXITCODE). Run the script again to resume."
    }
    Move-Item -Path $partial -Destination $out -Force
}

for ($i = 0; $i -lt $Parts; $i++) {
    $zip = Join-Path $dest "exams_part$i.zip"
    $marker = $zip + '.extracted'
    if (Test-Path $marker) { continue }
    Write-Host "Unzipping exams_part$i.zip"
    & tar.exe -xf $zip -C $dest
    if ($LASTEXITCODE -ne 0) { throw "Unzipping $zip failed." }
    New-Item -ItemType File -Force -Path $marker | Out-Null
}

Write-Host ''
Write-Host 'CODE-15% files now in data\code15:'
Get-ChildItem -Path $dest -Recurse -File |
    Where-Object { $_.Extension -eq '.csv' -or $_.Extension -eq '.hdf5' } |
    ForEach-Object { Write-Host ('  {0,-40} {1,8} MB' -f $_.Name, [math]::Round($_.Length / 1MB)) }
