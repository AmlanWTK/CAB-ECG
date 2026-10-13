# Downloads the Georgia (USA), CPSC 2018 and CPSC-Extra (China) training sets of the
# PhysioNet/CinC Challenge 2021 v1.0.3 into data\challenge2021\training.
#
# PhysioNet serves each connection at only about 10-20 KB/s, so one minimized wget
# window is started per subfolder (22 windows) and they run in parallel.
# Safe to re-run at any time: files that are already complete are skipped and
# incomplete ones are fetched again.
#
# Usage, from the repository root:
#   powershell -ExecutionPolicy Bypass -File scripts\download_challenge2021.ps1
#
# Then, when all wget windows have closed:
#   powershell -ExecutionPolicy Bypass -File scripts\check_challenge2021.ps1

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

# Locate wget.exe (install once with: winget install --id JernejSimoncic.Wget -e)
$wget = $null
$cmd = Get-Command wget.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if ($cmd) { $wget = $cmd.Source }
if (-not $wget) {
    $roots = @((Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet'), (Join-Path $env:ProgramFiles 'WinGet'))
    $hit = Get-ChildItem -Path $roots -Recurse -Filter wget.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($hit) { $wget = $hit.FullName }
}
if (-not $wget) {
    throw 'wget.exe not found. Install it with: winget install --id JernejSimoncic.Wget -e'
}
Write-Host "Using wget: $wget"

$base = 'https://physionet.org/files/challenge-2021/1.0.3/training'
$folders = @()
foreach ($i in 1..11) { $folders += "georgia/g$i" }
foreach ($i in 1..7)  { $folders += "cpsc_2018/g$i" }
foreach ($i in 1..4)  { $folders += "cpsc_2018_extra/g$i" }

# -N -c       skip complete files, resume or replace incomplete ones
# --tries=0   keep retrying when PhysioNet drops the connection
$wgetArgs = '-r -N -c -np -nH --cut-dirs=3 -R "index.html*" --tries=0 --waitretry=10 --retry-connrefused --read-timeout=60 -P data\challenge2021'

foreach ($f in $folders) {
    Start-Process -FilePath $wget -WindowStyle Minimized -ArgumentList "$wgetArgs $base/$f/"
}

Write-Host ''
Write-Host "Started $($folders.Count) minimized download windows."
Write-Host 'When they have all closed, check the result with:'
Write-Host '  powershell -ExecutionPolicy Bypass -File scripts\check_challenge2021.ps1'
