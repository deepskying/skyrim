[CmdletBinding()]
param(
    [string]$MO2 = 'C:\Users\linos\Desktop\games\+skyrim\MO2',
    [string]$SourceProfile = '-std-',
    [string]$TestProfile = '物品清单-Meridian测试'
)
$ErrorActionPreference = 'Stop'
$taskName = '界面模组-物品清单-InventoryManager-Meridian测试-🟩Shift+D'
$taskMods = [IO.Path]::GetFullPath((Join-Path $MO2 'mods'))
$taskProfiles = [IO.Path]::GetFullPath((Join-Path $MO2 'profiles'))
$taskDestination = [IO.Path]::GetFullPath((Join-Path $taskMods $taskName))
$taskProfile = [IO.Path]::GetFullPath((Join-Path $taskProfiles $TestProfile))
$taskSource = [IO.Path]::GetFullPath((Join-Path $taskProfiles $SourceProfile))
if (-not $taskDestination.StartsWith($taskMods + '\', [StringComparison]::OrdinalIgnoreCase) -or
    -not $taskProfile.StartsWith($taskProfiles + '\', [StringComparison]::OrdinalIgnoreCase) -or
    -not $taskSource.StartsWith($taskProfiles + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid MO2 destination.' }
if ((Test-Path -LiteralPath $taskDestination) -or (Test-Path -LiteralPath $taskProfile)) { throw 'Test mod/profile already exists; refusing to overwrite it.' }
$taskData = Join-Path $PSScriptRoot 'release\meridian\Data'
foreach ($taskRequired in @((Join-Path $taskData 'SKSE\Plugins\InventoryManager.dll'), (Join-Path $taskData 'MeridianUI\inventorymanager\index.html'), (Join-Path $taskSource 'modlist.txt'))) {
    if (-not (Test-Path -LiteralPath $taskRequired)) { throw "Missing $taskRequired" }
}
$taskMeridian = Get-ChildItem -LiteralPath $taskMods -Directory | Where-Object {
    Test-Path -LiteralPath (Join-Path $_.FullName 'SKSE\Plugins\MeridianUIPlugin.dll')
} | Select-Object -First 1
if (-not $taskMeridian) { throw 'Install Meridian UI 1.5.0 in MO2 first.' }
New-Item -ItemType Directory -Path $taskDestination, $taskProfile | Out-Null
Copy-Item -Path (Join-Path $taskData '*') -Destination $taskDestination -Recurse
foreach ($taskFile in @('modlist.txt','plugins.txt','loadorder.txt','lockedorder.txt','archives.txt','initweaks.ini','settings.ini','skyrim.ini','skyrimcustom.ini','skyrimprefs.ini')) {
    $taskFilePath = Join-Path $taskSource $taskFile
    if (Test-Path -LiteralPath $taskFilePath) { Copy-Item -LiteralPath $taskFilePath -Destination $taskProfile }
}
$taskLines = Get-Content -LiteralPath (Join-Path $taskProfile 'modlist.txt') -Encoding utf8
$taskLines = @('+' + $taskName) + @($taskLines | ForEach-Object {
    if ($_ -match '^[+-].*InventoryManager') { '-' + $_.Substring(1) }
    elseif ($_ -eq ('-' + $taskMeridian.Name)) { '+' + $taskMeridian.Name }
    else { $_ }
})
if ($taskLines -notcontains ('+' + $taskMeridian.Name)) { $taskLines += '+' + $taskMeridian.Name }
[IO.File]::WriteAllLines((Join-Path $taskProfile 'modlist.txt'), $taskLines, [Text.UTF8Encoding]::new($false))
foreach ($taskList in @('plugins.txt','loadorder.txt')) {
    $taskListPath = Join-Path $taskProfile $taskList
    $taskEntries = @(Get-Content -LiteralPath $taskListPath -Encoding utf8 | Where-Object { $_ -notmatch '^\*?InventoryManager\.esp$' })
    $taskEntries += $(if ($taskList -eq 'plugins.txt') { '*InventoryManager.esp' } else { 'InventoryManager.esp' })
    [IO.File]::WriteAllLines($taskListPath, $taskEntries, [Text.UTF8Encoding]::new($false))
}
# Copy one local save and its co-save into the isolated profile when available.
$taskSave = Get-ChildItem -LiteralPath (Join-Path $taskSource 'saves') -Filter '*.ess' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($taskSave) {
    $taskSaves = Join-Path $taskProfile 'saves'
    New-Item -ItemType Directory -Path $taskSaves | Out-Null
    Copy-Item -LiteralPath $taskSave.FullName -Destination $taskSaves
    $taskCoSave = [IO.Path]::ChangeExtension($taskSave.FullName, '.skse')
    if (Test-Path -LiteralPath $taskCoSave) { Copy-Item -LiteralPath $taskCoSave -Destination $taskSaves }
}
Write-Host "Installed $taskName"
Write-Host "Select MO2 profile: $TestProfile (original profile unchanged)"
