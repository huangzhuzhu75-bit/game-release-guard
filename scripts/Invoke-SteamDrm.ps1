<# This opt-in operation uploads the input executable to Valve. It never uploads a depot or changes a live branch. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$SteamCmd,
    [Parameter(Mandatory=$true)][ValidateRange(1, 2147483647)][int]$AppId,
    [Parameter(Mandatory=$true)][string]$InputExe,
    [Parameter(Mandatory=$true)][string]$OutputExe,
    [string]$Account,
    [ValidateSet(0, 6, 32, 38)][int]$Flags = 0,
    [switch]$AcknowledgeExecutableUpload
)
$ErrorActionPreference = 'Stop'
if (-not $AcknowledgeExecutableUpload) {
    throw 'This operation uploads your executable to Valve. Review Steamworks DRM documentation, then explicitly pass -AcknowledgeExecutableUpload.'
}
$srgSteam = (Resolve-Path -LiteralPath $SteamCmd).Path
$srgInput = (Resolve-Path -LiteralPath $InputExe).Path
$srgOutput = [System.IO.Path]::GetFullPath($OutputExe)
if ([System.IO.Path]::GetFileName($srgSteam) -ine 'steamcmd.exe') { throw 'Select your authorized Steamworks steamcmd.exe.' }
if ([System.IO.Path]::GetExtension($srgInput) -ine '.exe' -or [System.IO.Path]::GetExtension($srgOutput) -ine '.exe') { throw 'Input and output must be .exe files.' }
if ($srgInput -ieq $srgOutput -or (Test-Path -LiteralPath $srgOutput)) { throw 'Choose a new output executable. The original and existing outputs are preserved.' }
if (-not (Test-Path -LiteralPath (Split-Path -Parent $srgOutput) -PathType Container)) { throw 'Create the output directory first.' }
if (-not $Account) { $Account = Read-Host 'Steamworks build account (SteamCMD will request authentication)' }
if ($Account -notmatch '^[A-Za-z0-9_]+$') { throw 'Invalid account name.' }
$srgHash = (Get-FileHash -LiteralPath $srgInput -Algorithm SHA256).Hash
$srgArguments = @('+login', $Account, '+drm_wrap', [string]$AppId, $srgInput, $srgOutput, 'drmtoolp', [string]$Flags, '+quit')
& $srgSteam @srgArguments
if ($LASTEXITCODE -ne 0) { throw "SteamCMD failed: $LASTEXITCODE" }
if (-not (Test-Path -LiteralPath $srgOutput -PathType Leaf) -or (Get-Item -LiteralPath $srgOutput).Length -eq 0) { throw 'SteamCMD did not produce the wrapped executable. Inspect its log.' }
if ((Get-FileHash -LiteralPath $srgInput -Algorithm SHA256).Hash -ne $srgHash) { throw 'The original executable changed unexpectedly; investigate before distribution.' }
Write-Host "Wrapped output: $srgOutput"
Write-Host 'This is not launch approval. Replace the executable only in a new staging copy, apply any required code signing, then reinstall and test from a Steam test branch.'
