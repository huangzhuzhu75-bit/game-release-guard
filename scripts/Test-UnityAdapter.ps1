[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$UnityEditor,
    [string]$OutputDirectory = (Join-Path (Split-Path -Parent $PSScriptRoot) '.artifacts/unity-compile')
)
$ErrorActionPreference = 'Stop'
$srgData = Join-Path (Split-Path -Parent (Resolve-Path -LiteralPath $UnityEditor).Path) 'Data'
$srgDotnet = Join-Path $srgData 'NetCoreRuntime/dotnet.exe'
$srgCompilers = @(Get-ChildItem -Path (Join-Path $srgData 'DotNetSdk/sdk/*/Roslyn/bincore/csc.dll'))
if ($srgCompilers.Count -ne 1) { throw 'Expected one C# compiler from this Unity installation; review the engine SDK layout.' }
$srgOutput = [System.IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $srgOutput -Force | Out-Null
$env:DOTNET_CLI_HOME = Join-Path $srgOutput 'dotnet-home'
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE = '1'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$srgReferences = @(
    Get-ChildItem -LiteralPath (Join-Path $srgData 'UnityReferenceAssemblies/unity-4.8-api') -Filter '*.dll'
    Get-ChildItem -LiteralPath (Join-Path $srgData 'UnityReferenceAssemblies/unity-4.8-api/Facades') -Filter '*.dll'
    Get-ChildItem -LiteralPath (Join-Path $srgData 'Managed/UnityEngine') -Filter '*.dll'
)
$srgLines = @('-nologo', '-nostdlib+', '-target:library', '-define:UNITY_EDITOR;UNITY_6000_0_OR_NEWER')
$srgLines += '-out:"' + (Join-Path $srgOutput 'SteamReleaseGuard.Editor.dll') + '"'
$srgLines += @($srgReferences | ForEach-Object { '-r:"' + $_.FullName + '"' })
$srgLines += '"' + (Join-Path (Split-Path -Parent $PSScriptRoot) 'adapters/unity/SteamReleaseGuardBuild.cs') + '"'
$srgResponse = Join-Path $srgOutput 'compile.rsp'
$srgLines | Set-Content -LiteralPath $srgResponse -Encoding utf8
& $srgDotnet $srgCompilers[0].FullName -noconfig ('@' + $srgResponse)
if ($LASTEXITCODE -ne 0) { throw "Unity adapter compilation failed: $LASTEXITCODE" }
Write-Host 'Compiled against the installed Unity Editor API. This does not execute Unity or prove a successful IL2CPP game build.'
