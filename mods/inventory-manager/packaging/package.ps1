[CmdletBinding()]
param(
    [string]$OutputDirectory = (Join-Path $PSScriptRoot "release"),
    [string]$Version
)

$moduleRoot = Split-Path -Parent $PSScriptRoot
$packageManifestPath = Join-Path $moduleRoot "web\package.json"
$dllPath = Join-Path $moduleRoot "native\build\windows\x64\release\InventoryManager.dll"
$viewSource = Join-Path $moduleRoot "web\dist"
$iniPath = Join-Path $PSScriptRoot "InventoryManager.ini"

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = (Get-Content -LiteralPath $packageManifestPath -Raw | ConvertFrom-Json).version
}
if ([string]::IsNullOrWhiteSpace($Version)) {
    throw "Package version is missing from $packageManifestPath"
}

foreach ($requiredPath in @($dllPath, $viewSource, $iniPath)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required build output is missing: $requiredPath"
    }
}

$pluginDestination = Join-Path $OutputDirectory "Data\SKSE\Plugins"
$viewDestination = Join-Path $OutputDirectory "Data\PrismaUI\views\InventoryManager"
New-Item -ItemType Directory -Force -Path $pluginDestination, $viewDestination | Out-Null

Copy-Item -LiteralPath $dllPath -Destination (Join-Path $pluginDestination "InventoryManager.dll") -Force
Copy-Item -LiteralPath $iniPath -Destination (Join-Path $pluginDestination "InventoryManager.ini") -Force
Copy-Item -Path (Join-Path $viewSource "*") -Destination $viewDestination -Recurse -Force

$archivePath = Join-Path $PSScriptRoot ("InventoryManager-{0}.zip" -f $Version)
Compress-Archive -LiteralPath (Join-Path $OutputDirectory "Data") -DestinationPath $archivePath -Force

Write-Host "Package ready at: $OutputDirectory"
Write-Host "Archive ready at: $archivePath"
