[CmdletBinding()]
param([string]$OutputDirectory = (Join-Path $PSScriptRoot 'release'))
$ErrorActionPreference = 'Stop'
$taskModule = Split-Path $PSScriptRoot -Parent
$taskDll = Join-Path $taskModule 'native\build\windows\x64\release\MusicManager.dll'
$taskWeb = Join-Path $taskModule 'web\dist'
foreach ($taskRequired in @($taskDll, (Join-Path $taskWeb 'index.html'))) {
    if (-not (Test-Path -LiteralPath $taskRequired)) { throw "Missing build output: $taskRequired" }
}
$taskPlugins = Join-Path $OutputDirectory 'Data\SKSE\Plugins'
$taskView = Join-Path $OutputDirectory 'Data\PrismaUI\views\MusicManager'
New-Item -ItemType Directory -Force -Path $taskPlugins,$taskView | Out-Null
Copy-Item -LiteralPath $taskDll -Destination $taskPlugins -Force
foreach ($taskConfig in @('MusicManager.ini','MusicManager.rules.json')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $taskConfig) -Destination $taskPlugins -Force
}
Get-ChildItem -LiteralPath $taskWeb -File | Copy-Item -Destination $taskView -Force
foreach ($taskFolder in @('野外白天','野外夜晚','城镇','酒馆','住宅','地牢','普通战斗','龙战','通用')) {
    $taskFolderPath = Join-Path $OutputDirectory "Data\Music\MusicManager\$taskFolder"
    New-Item -ItemType Directory -Force -Path $taskFolderPath | Out-Null
    Set-Content -LiteralPath (Join-Path $taskFolderPath '放入音乐.txt') -Value '将 MP3、FLAC 或 WAV 放入此文件夹，无须重命名。在游戏内 Shift+M → 重新扫描。' -Encoding utf8
}
Copy-Item -LiteralPath (Join-Path $taskModule 'README.md') -Destination $OutputDirectory -Force
Copy-Item -LiteralPath (Join-Path $taskModule 'native\vendor\LICENSE.miniaudio') -Destination $OutputDirectory -Force
$taskZip = Join-Path $PSScriptRoot 'MusicManager-0.2.0-MO2.zip'
# Keep release/Data for the local installer, but put Data's contents directly
# at the archive root for MO2. Explicit inputs exclude stale/personal files.
Add-Type -AssemblyName System.IO.Compression.FileSystem
$taskArchiveStream = [IO.File]::Open($taskZip, [IO.FileMode]::Create)
$taskArchive = [IO.Compression.ZipArchive]::new($taskArchiveStream, [IO.Compression.ZipArchiveMode]::Create, $false, [Text.Encoding]::UTF8)
try {
    $taskEntries = @(
        'SKSE/Plugins/MusicManager.dll',
        'SKSE/Plugins/MusicManager.ini',
        'SKSE/Plugins/MusicManager.rules.json',
        'PrismaUI/views/MusicManager/index.html',
        'PrismaUI/views/MusicManager/app.js',
        'PrismaUI/views/MusicManager/styles.css'
    )
    foreach ($taskFolder in @('野外白天','野外夜晚','城镇','酒馆','住宅','地牢','普通战斗','龙战','通用')) {
        $taskEntries += "Music/MusicManager/$taskFolder/放入音乐.txt"
    }
    foreach ($taskEntry in $taskEntries) {
        $taskSource = Join-Path (Join-Path $OutputDirectory 'Data') $taskEntry
        [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($taskArchive, $taskSource, $taskEntry) | Out-Null
    }
    foreach ($taskEntry in @('README.md','LICENSE.miniaudio')) {
        [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($taskArchive, (Join-Path $OutputDirectory $taskEntry), $taskEntry) | Out-Null
    }
} finally {
    $taskArchive.Dispose()
    $taskArchiveStream.Dispose()
}
Write-Output "Package: $taskZip"
