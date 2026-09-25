[CmdletBinding()]
param(
    [string]$MO2 = 'C:\Users\linos\Desktop\games\+skyrim\MO2',
    [string]$SourceProfile = '-std-',
    [string]$TestProfile = '音乐管理器-测试'
)
$ErrorActionPreference = 'Stop'
$taskName = '音乐模组-音乐管理器-Music Manager-Shift+M'
$taskModsRoot = [IO.Path]::GetFullPath((Join-Path $MO2 'mods'))
$taskProfilesRoot = [IO.Path]::GetFullPath((Join-Path $MO2 'profiles'))
$taskDestination = [IO.Path]::GetFullPath((Join-Path $taskModsRoot $taskName))
$taskProfile = [IO.Path]::GetFullPath((Join-Path $taskProfilesRoot $TestProfile))
$taskSource = [IO.Path]::GetFullPath((Join-Path $taskProfilesRoot $SourceProfile))
if (-not $taskDestination.StartsWith($taskModsRoot + '\', [StringComparison]::OrdinalIgnoreCase) -or -not $taskProfile.StartsWith($taskProfilesRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Destination escaped the MO2 directories.' }
if (Test-Path -LiteralPath $taskDestination) { throw 'This installer creates a new mod only; destination already exists.' }
if (Test-Path -LiteralPath $taskProfile) { throw 'Test profile already exists; refusing to overwrite it.' }
$taskRelease = Join-Path $PSScriptRoot 'release'
$taskVersion = (Get-Content -LiteralPath (Join-Path $PSScriptRoot '..\web\package.json') -Raw | ConvertFrom-Json).version
$taskArchive = Join-Path $PSScriptRoot "MusicManager-$taskVersion-MO2.zip"
$taskPython = (Get-Command python -ErrorAction Stop).Source
$taskMigration = Join-Path $PSScriptRoot 'migration\mp3-v0.3.0'
$taskReport = Get-Content -LiteralPath (Join-Path $taskMigration 'migration-report.json') -Raw -Encoding utf8 | ConvertFrom-Json
if ($taskReport.errors.Count -gt 0) { throw 'Migration has unresolved errors.' }
$taskDependencies = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'validation\dcs-dependencies.json') -Raw -Encoding utf8 | ConvertFrom-Json
if ($taskDependencies.dependents.Count -gt 0 -or $taskDependencies.missing.Count -gt 0) { throw 'DCS dependency check has unresolved entries.' }
foreach ($taskRequired in @($taskArchive,(Join-Path $taskRelease 'Data\MusicManager.esp'),(Join-Path $taskRelease 'Data\SKSE\Plugins\MusicManager.dll'),(Join-Path $taskSource 'modlist.txt'),(Join-Path $taskMigration 'Data\Music\MusicManager'))) {
    if (-not (Test-Path -LiteralPath $taskRequired)) { throw "Missing: $taskRequired" }
}
New-Item -ItemType Directory -Path $taskDestination,$taskProfile | Out-Null
# Use the package whitelist rather than potentially stale release staging folders.
Expand-Archive -LiteralPath $taskArchive -DestinationPath $taskDestination
$taskMusicSource = Join-Path $taskMigration 'Data\Music\MusicManager'
$taskMusicDestination = Join-Path $taskDestination 'Music\MusicManager'
Get-ChildItem -LiteralPath $taskMusicSource -Directory | ForEach-Object {
    $taskCategoryTarget = Join-Path $taskMusicDestination $_.Name
    New-Item -ItemType Directory -Force -Path $taskCategoryTarget | Out-Null
    Get-ChildItem -LiteralPath $_.FullName -File | Copy-Item -Destination $taskCategoryTarget
}
if ((Test-Path -LiteralPath (Join-Path $taskMusicDestination '野外白天')) -or (Test-Path -LiteralPath (Join-Path $taskMusicDestination '野外夜晚'))) {
    $taskMergeBackup = Join-Path $PSScriptRoot ('validation\install-exploration-' + [Guid]::NewGuid().ToString('N'))
    & $taskPython (Join-Path $PSScriptRoot '..\tools\merge_exploration.py') --library $taskMusicDestination --backup $taskMergeBackup
    if ($LASTEXITCODE -ne 0) { throw 'Exploration merge failed; see backup before continuing installation.' }
    Copy-Item -LiteralPath (Join-Path $taskMergeBackup 'merge-receipt.json') -Destination (Join-Path $taskDestination 'exploration-merge-report.json')
}
Copy-Item -LiteralPath (Join-Path $taskMigration 'migration-report.json'),(Join-Path $taskRelease 'README.md'),(Join-Path $taskRelease 'LICENSE.miniaudio') -Destination $taskDestination
$taskIni = Get-Content -LiteralPath (Join-Path $taskDestination 'SKSE\Plugins\MusicManager.ini') -Raw
$taskIni = $taskIni -replace '(?m)^Path=.*$', ('Path=' + $taskMusicDestination)
# Win32 INI APIs need UTF-16 for Chinese physical paths.
[IO.File]::WriteAllText((Join-Path $taskDestination 'SKSE\Plugins\MusicManager.ini'),$taskIni,[Text.Encoding]::Unicode)
$taskMeta = "[General]`r`ngameName=SkyrimSE`r`nversion=$taskVersion`r`nmodid=0`r`nrepository=Local`r`nnotes=Shift+M music manager; tested in separate profile.`r`n"
[IO.File]::WriteAllText((Join-Path $taskDestination 'meta.ini'),$taskMeta,[Text.UTF8Encoding]::new($false))
foreach ($taskFile in @('archives.txt','initweaks.ini','loadorder.txt','lockedorder.txt','settings.ini','skyrim.ini','skyrimcustom.ini','skyrimprefs.ini','plugins.txt','modlist.txt')) {
    $taskSourceFile = Join-Path $taskSource $taskFile
    if (Test-Path -LiteralPath $taskSourceFile) { Copy-Item -LiteralPath $taskSourceFile -Destination $taskProfile }
}
$taskDcs = @('音乐模组-背景音效-DCS-Dynamic Customizable Soundtrack Music SE','----资源-DCS-城镇','----资源-DCS-地牢','----资源-DCS-探索背景音乐','----资源-DCS-战斗背景音乐')
$taskModlistPath = Join-Path $taskProfile 'modlist.txt'
$taskLines = [IO.File]::ReadAllLines($taskModlistPath,[Text.Encoding]::UTF8)
$taskNewLines = [Collections.Generic.List[string]]::new()
$taskNewLines.Add('# This file was automatically generated by Mod Organizer.')
$taskNewLines.Add('+' + $taskName)
foreach ($taskLine in $taskLines) {
    if ($taskLine.StartsWith('#')) { continue }
    if ($taskLine.Length -gt 1 -and $taskDcs -contains $taskLine.Substring(1)) { $taskNewLines.Add('-' + $taskLine.Substring(1)) }
    else { $taskNewLines.Add($taskLine) }
}
[IO.File]::WriteAllLines($taskModlistPath,$taskNewLines,[Text.UTF8Encoding]::new($false))
$taskPluginPath = Join-Path $taskProfile 'plugins.txt'
$taskPlugins = [IO.File]::ReadAllLines($taskPluginPath,[Text.Encoding]::UTF8) | ForEach-Object { if ($_ -match '^\*DCS - ') { $_.Substring(1) } else { $_ } }
$taskPlugins = @($taskPlugins | Where-Object { $_ -notmatch '^\*?MusicManager\.esp$' }) + '*MusicManager.esp'
[IO.File]::WriteAllLines($taskPluginPath,$taskPlugins,[Text.UTF8Encoding]::new($false))
$taskLoadOrderPath = Join-Path $taskProfile 'loadorder.txt'
$taskLoadOrder = @()
if (Test-Path -LiteralPath $taskLoadOrderPath) { $taskLoadOrder = @([IO.File]::ReadAllLines($taskLoadOrderPath,[Text.Encoding]::UTF8) | Where-Object { $_ -ne 'MusicManager.esp' }) }
$taskLoadOrder += 'MusicManager.esp'
[IO.File]::WriteAllLines($taskLoadOrderPath,$taskLoadOrder,[Text.UTF8Encoding]::new($false))
# Copy only the latest save and its co-save into the isolated profile.
$taskSaves = Join-Path $taskSource 'saves'
$taskSaveTarget = Join-Path $taskProfile 'saves'
New-Item -ItemType Directory -Path $taskSaveTarget | Out-Null
$taskLatest = Get-ChildItem -LiteralPath $taskSaves -Filter '*.ess' -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($taskLatest) {
    Copy-Item -LiteralPath $taskLatest.FullName -Destination $taskSaveTarget
    $taskCosave = [IO.Path]::ChangeExtension($taskLatest.FullName,'.skse')
    if (Test-Path -LiteralPath $taskCosave) { Copy-Item -LiteralPath $taskCosave -Destination $taskSaveTarget }
}
$taskExpectedHash = (Get-FileHash -LiteralPath (Join-Path $taskRelease 'Data\SKSE\Plugins\MusicManager.dll')).Hash
$taskInstalledHash = (Get-FileHash -LiteralPath (Join-Path $taskDestination 'SKSE\Plugins\MusicManager.dll')).Hash
if ($taskExpectedHash -ne $taskInstalledHash) { throw 'Installed DLL hash mismatch.' }
$taskCount = @(Get-ChildItem -LiteralPath $taskMusicDestination -Recurse -File | Where-Object Extension -in '.mp3','.wav','.flac').Count
$taskReceipt = [ordered]@{mod=$taskDestination;profile=$taskProfile;music=$taskMusicDestination;tracks=$taskCount;dllSha256=$taskInstalledHash;originalProfileUnchanged=$taskSource;latestSaveCopied=[bool]$taskLatest;installedAt=(Get-Date -Format o)}
$taskReceipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'validation\install-receipt.json') -Encoding utf8
$taskReceipt | ConvertTo-Json
