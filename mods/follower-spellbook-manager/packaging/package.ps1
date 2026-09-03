[CmdletBinding()]
param(
    [string]$Version
)

$moduleRoot = Split-Path -Parent $PSScriptRoot
$packageManifestPath = Join-Path $moduleRoot "web\package.json"
$dllPath = Join-Path $moduleRoot "native\build\windows\x64\release\FollowerSpellbookManager.dll"
$viewSource = Join-Path $moduleRoot "web\dist"
$iniPath = Join-Path $PSScriptRoot "FollowerSpellbookManager.ini"

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

$stageRoot = Join-Path $PSScriptRoot ("FollowerSpellbookManager-{0}" -f $Version)
if (Test-Path -LiteralPath $stageRoot) {
    throw "Refusing to overwrite existing package staging directory: $stageRoot"
}

$pluginDestination = Join-Path $stageRoot "SKSE\Plugins"
$viewDestination = Join-Path $stageRoot "PrismaUI\views\FollowerSpellbookManager"
New-Item -ItemType Directory -Force -Path $pluginDestination, $viewDestination | Out-Null
Copy-Item -LiteralPath $dllPath -Destination (Join-Path $pluginDestination "FollowerSpellbookManager.dll")
Copy-Item -LiteralPath $iniPath -Destination (Join-Path $pluginDestination "FollowerSpellbookManager.ini")
Copy-Item -Path (Join-Path $viewSource "*") -Destination $viewDestination -Recurse

$archivePath = Join-Path $PSScriptRoot ("FollowerSpellbookManager-{0}.zip" -f $Version)
Compress-Archive -Path (Join-Path $stageRoot "*") -DestinationPath $archivePath

Write-Host "Package ready at: $stageRoot"
Write-Host "Archive ready at: $archivePath"
