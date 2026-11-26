[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$UnityEditor,
    [Parameter(Mandatory=$true)][string]$ObfuzSource,
    [Parameter(Mandatory=$true)][string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
$srgRoot = Split-Path -Parent $PSScriptRoot
$srgData = Join-Path (Split-Path -Parent (Resolve-Path -LiteralPath $UnityEditor).Path) 'Data'
$srgObfuz = (Resolve-Path -LiteralPath $ObfuzSource).Path
$srgPackage = Get-Content -LiteralPath (Join-Path $srgObfuz 'package.json') -Raw | ConvertFrom-Json
if ($srgPackage.name -ne 'com.code-philosophy.obfuz' -or $srgPackage.version -ne '4.0.0') { throw 'Expected reviewed Obfuz 4.0.0 source.' }
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new output directory.' }
New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
$srgOutput = (Resolve-Path -LiteralPath $OutputDirectory).Path
$env:DOTNET_CLI_HOME = Join-Path $srgOutput 'dotnet-home'
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE = '1'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$srgDotnet = Join-Path $srgData 'NetCoreRuntime/dotnet.exe'
$srgCompiler = @(Get-ChildItem -Path (Join-Path $srgData 'DotNetSdk/sdk/*/Roslyn/bincore/csc.dll'))
if ($srgCompiler.Count -ne 1) { throw 'Unexpected Unity compiler layout.' }
$srgReferences = @(
    Get-ChildItem -LiteralPath (Join-Path $srgData 'UnityReferenceAssemblies/unity-4.8-api') -Filter '*.dll'
    Get-ChildItem -LiteralPath (Join-Path $srgData 'UnityReferenceAssemblies/unity-4.8-api/Facades') -Filter '*.dll'
    Get-ChildItem -LiteralPath (Join-Path $srgData 'Managed/UnityEngine') -Filter '*.dll'
)
function Invoke-SrgCompile([string]$Name, [string[]]$Sources, [string[]]$Extra) {
    $srgArgs = @('-nologo', '-nostdlib+', '-target:library', '-unsafe+', '-define:UNITY_EDITOR;UNITY_EDITOR_WIN;UNITY_STANDALONE_WIN;UNITY_6000_0_OR_NEWER;UNITY_2019_1_OR_NEWER;UNITY_2022_1_OR_NEWER;UNITY_2023_1_OR_NEWER;UNITY_6000_3_OR_NEWER')
    $srgArgs += '-out:"' + (Join-Path $srgOutput ($Name + '.dll')) + '"'
    $srgArgs += @($srgReferences | ForEach-Object { '-r:"' + $_.FullName + '"' })
    $srgArgs += @($Extra | ForEach-Object { '-r:"' + $_ + '"' })
    $srgArgs += @($Sources | ForEach-Object { '"' + $_ + '"' })
    $srgResponse = Join-Path $srgOutput ($Name + '.rsp')
    $srgArgs | Set-Content -LiteralPath $srgResponse -Encoding utf8
    & $srgDotnet $srgCompiler[0].FullName -noconfig ('@' + $srgResponse)
    if ($LASTEXITCODE -ne 0) { throw "Compilation failed: $Name" }
}
Invoke-SrgCompile 'Obfuz.Runtime' @(Get-ChildItem -LiteralPath (Join-Path $srgObfuz 'Runtime') -Recurse -Filter '*.cs' | ForEach-Object FullName) @()
Invoke-SrgCompile 'Obfuz.Editor' @(Get-ChildItem -LiteralPath (Join-Path $srgObfuz 'Editor') -Recurse -Filter '*.cs' | ForEach-Object FullName) @((Join-Path $srgOutput 'Obfuz.Runtime.dll'), (Join-Path $srgObfuz 'Plugins/dnlib.dll'))
Invoke-SrgCompile 'SteamReleaseGuard.Editor' @((Join-Path $srgRoot 'adapters/unity/SteamReleaseGuardBuild.cs')) @()
Invoke-SrgCompile 'SteamReleaseGuard.Obfuscation.Editor' @((Join-Path $srgRoot 'adapters/unity-advanced/SteamReleaseGuardObfuscation.cs')) @((Join-Path $srgOutput 'SteamReleaseGuard.Editor.dll'), (Join-Path $srgOutput 'Obfuz.Runtime.dll'), (Join-Path $srgOutput 'Obfuz.Editor.dll'), (Join-Path $srgObfuz 'Plugins/dnlib.dll'))
Write-Host 'Compiled against actual Unity and Obfuz APIs. Game build, obfuscation execution and runtime are NOT_VERIFIED.'
