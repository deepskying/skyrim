[CmdletBinding()]
param([string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $PSScriptRoot 'release' }
$taskModule = Split-Path $PSScriptRoot -Parent
$taskDll = Join-Path $taskModule 'native\build\windows\x64\release\MainMenuManager.dll'
if (-not (Test-Path -LiteralPath $taskDll)) { throw "Build MainMenuManager first: $taskDll" }
$taskBrowser = Join-Path $taskModule 'build\browser\开屏背景管理器.exe'
if (-not (Test-Path -LiteralPath $taskBrowser)) { throw 'Build browser/build.ps1 first.' }
$taskRelease = [IO.Path]::GetFullPath($OutputDirectory)
$taskInputs = [ordered]@{
    'SKSE/Plugins/MainMenuManager.dll' = $taskDll
    'SKSE/Plugins/MainMenuManager.json' = (Join-Path $PSScriptRoot 'MainMenuManager.json')
    'MainMenuManager/backgrounds/放入背景.txt' = (Join-Path $PSScriptRoot 'backgrounds\放入背景.txt')
    'MainMenuManager/backgrounds/_example/theme.json' = (Join-Path $PSScriptRoot 'backgrounds\_example\theme.json')
    'MainMenuManager/backgrounds/_example/Data/放入配套资源.txt' = (Join-Path $PSScriptRoot 'backgrounds\_example\Data\放入配套资源.txt')
    'MainMenuManager/tools/New-ImageTheme.ps1' = (Join-Path $taskModule 'tools\New-ImageTheme.ps1')
    'MainMenuManager/tools/remove_dragon_logo.py' = (Join-Path $taskModule 'tools\remove_dragon_logo.py')
    'MainMenuManager/README.md' = (Join-Path $taskModule 'README.md')
    'MainMenuManager/开屏背景管理器.exe' = $taskBrowser
    'MainMenuManager/开屏背景管理器.exe.config' = (Join-Path $taskModule 'browser\App.config')
    'MainMenuManager/loading-backgrounds/放入加载背景.txt' = (Join-Path $PSScriptRoot 'loading-backgrounds\放入加载背景.txt')
}
foreach ($taskEntry in $taskInputs.GetEnumerator()) {
    $taskDestination = Join-Path $taskRelease $taskEntry.Key
    $null = New-Item -ItemType Directory -Force -Path (Split-Path $taskDestination -Parent)
    Copy-Item -LiteralPath $taskEntry.Value -Destination $taskDestination -Force
}
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -AssemblyName System.IO.Compression
$taskZipPath = Join-Path $PSScriptRoot 'sky-backgrounds-0.2.1-mo2.zip'
$taskStream = [IO.File]::Open($taskZipPath, [IO.FileMode]::Create)
$taskZip = [IO.Compression.ZipArchive]::new($taskStream, [IO.Compression.ZipArchiveMode]::Create, $false, [Text.Encoding]::UTF8)
try {
    # Explicit file list excludes state/backups and personal themes from releases.
    foreach ($taskEntry in $taskInputs.GetEnumerator()) {
        $null = [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($taskZip, (Join-Path $taskRelease $taskEntry.Key), $taskEntry.Key)
    }
} finally { $taskZip.Dispose(); $taskStream.Dispose() }
Write-Output "Package: $taskZipPath"
