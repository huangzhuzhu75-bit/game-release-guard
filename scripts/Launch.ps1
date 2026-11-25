$ErrorActionPreference = 'Stop'
$srgRoot = Split-Path -Parent $PSScriptRoot
$srgCandidates = @()
if ($env:SRG_PYTHON) { $srgCandidates += [pscustomobject]@{ Executable = $env:SRG_PYTHON; Prefix = @() } }
if (Test-Path -LiteralPath (Join-Path $srgRoot '.local/python-path.txt')) {
    $srgCandidates += [pscustomobject]@{ Executable = (Get-Content -LiteralPath (Join-Path $srgRoot '.local/python-path.txt') -Raw -Encoding UTF8).Trim(); Prefix = @() }
}
foreach ($srgName in @('py', 'python3', 'python')) {
    $srgCommand = Get-Command $srgName -ErrorAction SilentlyContinue
    if ($srgCommand) {
        $srgPrefix = @()
        if ($srgName -eq 'py') { $srgPrefix = @('-3') }
        $srgCandidates += [pscustomobject]@{ Executable = $srgCommand.Source; Prefix = $srgPrefix }
    }
}
foreach ($srgCandidate in $srgCandidates) {
    $srgExecutable = $srgCandidate.Executable
    $srgPrefix = $srgCandidate.Prefix
    if (-not (Test-Path -LiteralPath $srgExecutable -PathType Leaf)) { continue }
    & $srgExecutable @srgPrefix -c 'import sys; import tkinter; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>$null
    if ($LASTEXITCODE -eq 0) {
        Push-Location -LiteralPath $srgRoot
        try {
            $env:PYTHONDONTWRITEBYTECODE = '1'
            & $srgExecutable @srgPrefix -m steam_release_guard gui
            exit $LASTEXITCODE
        } finally { Pop-Location }
    }
}
Write-Host 'Python 3.10+ with tkinter is required. Set SRG_PYTHON to an existing python.exe, then double-click Launch.cmd again.'
Write-Host 'Nothing was installed or downloaded. See README.md for setup.'
exit 1
