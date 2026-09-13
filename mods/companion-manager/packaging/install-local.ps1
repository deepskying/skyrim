[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$PackageDirectory,
    [string]$MO2Root = 'C:/Users/linos/Desktop/games/+skyrim/MO2'
)
$ErrorActionPreference = 'Stop'
if (Get-Process SkyrimSE,skse64_loader -ErrorAction SilentlyContinue) { throw 'Exit Skyrim and SKSE before updating. MO2 snapshots its virtual file list at launch; new hashed UI assets cannot be hot-installed safely.' }
$source = (Resolve-Path -LiteralPath $PackageDirectory).Path
$mods = (Resolve-Path -LiteralPath (Join-Path $MO2Root 'mods')).Path
$frameworks = @(Get-ChildItem -LiteralPath $mods -Directory | Where-Object {
    (Test-Path -LiteralPath (Join-Path $_.FullName 'SKSE/Plugins/MeridianUIPlugin.dll')) -and
    (Test-Path -LiteralPath (Join-Path $_.FullName 'MeridianUI/MeridianUI.dll'))
})
if ($frameworks.Count -eq 0) { throw 'Install Meridian UI in this MO2 instance first.' }
$manifest = Get-Content -LiteralPath (Join-Path $source 'manifest.json') -Raw | ConvertFrom-Json
if ($manifest.stage -ne 'fulltest') { throw 'This installer requires the complete integration test package.' }
foreach ($entry in $manifest.files) {
    $path = [IO.Path]::GetFullPath((Join-Path $source $entry.path))
    if (-not $path.StartsWith($source + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid package path' }
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $entry.sha256) { throw "Package hash mismatch: $($entry.path)" }
}
foreach ($required in @('SKSE/Plugins/CompanionManager.dll', 'MeridianUI/companion-manager/index.html', 'CompanionManager.esp', 'Scripts/CMController.pex')) {
    if ($required -notin $manifest.files.path) { throw "Required package entry missing: $required" }
}
$existing = @(Get-ChildItem -LiteralPath $mods -Directory | Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'SKSE/Plugins/CompanionManager.dll') })
if ($existing.Count -gt 1) { throw 'Multiple CompanionManager installations found; resolve duplicate DLLs first.' }
$destination = if ($existing.Count) { $existing[0].FullName } else { Join-Path $mods '随从管理-CompanionManager-Shift+F' }
$destination = [IO.Path]::GetFullPath($destination)
if (-not $destination.StartsWith($mods + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Destination outside MO2 mods' }
if (Test-Path -LiteralPath $destination) {
    $backup = Join-Path $MO2Root "companion-manager-backups/$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    if (Test-Path -LiteralPath $backup) { throw 'Backup path already exists' }
    New-Item -ItemType Directory -Path $backup -Force | Out-Null
    Copy-Item -LiteralPath $destination -Destination $backup -Recurse
    Write-Output "Previous installation backed up outside the active mods folder: $backup"
} else { New-Item -ItemType Directory -Path $destination | Out-Null }
foreach ($entry in $manifest.files) {
    $target = Join-Path $destination $entry.path
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
    Copy-Item -LiteralPath (Join-Path $source $entry.path) -Destination $target
    if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $entry.sha256) { throw "Installed hash mismatch: $($entry.path)" }
}
Copy-Item -LiteralPath (Join-Path $source 'manifest.json') -Destination $destination
$metaPath = Join-Path $destination 'meta.ini'
if (Test-Path -LiteralPath $metaPath) {
    $meta = Get-Content -LiteralPath $metaPath -Raw
    $meta = [regex]::Replace($meta, '(?m)^version=.*$', "version=$($manifest.version)")
    $meta = [regex]::Replace($meta, '(?m)^notes=.*$', 'notes=Complete follower manager test build. Enable CompanionManager.esp. Shift+F.')
    Set-Content -LiteralPath $metaPath -Value $meta -Encoding utf8
} else { @"
[General]
gameName=Skyrim Special Edition
modid=0
version=$($manifest.version)
notes=Complete follower manager test build. Enable CompanionManager.esp. Shift+F.
"@ | Set-Content -LiteralPath $metaPath -Encoding utf8 }
Write-Output "Installed and hash-verified: $destination"
Write-Output 'MO2 profiles were not edited. Refresh MO2 and enable CompanionManager.esp in the right-hand Plugins pane.'
