$ErrorActionPreference = 'Stop'
$module = Split-Path -Parent $PSScriptRoot
$binary = Join-Path $module 'native\build\windows\x64\release\PeakEffectLoopGuard.dll'
if (!(Test-Path -LiteralPath $binary)) { throw 'Build the native plugin first.' }
$release = Join-Path $PSScriptRoot 'release'
$plugins = Join-Path $release 'SKSE\Plugins'
New-Item -ItemType Directory -Path $plugins -Force | Out-Null
Copy-Item -LiteralPath $binary -Destination $plugins -Force
Copy-Item -LiteralPath (Join-Path $module 'README.md') -Destination $release -Force
$archive = Join-Path $PSScriptRoot 'PeakEffectLoopGuard-0.1.0.zip'
Compress-Archive -LiteralPath (Join-Path $release 'SKSE'),(Join-Path $release 'README.md') -DestinationPath $archive -Force
Get-FileHash -LiteralPath $binary,$archive -Algorithm SHA256
