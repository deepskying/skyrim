[CmdletBinding()]
param(
    [string]$OutputDirectory = (Join-Path $PSScriptRoot "release"),
    [string]$Version
)

$moduleRoot = Split-Path -Parent $PSScriptRoot
$manifestPath = Join-Path $moduleRoot "web\package.json"
$dllPath = Join-Path $moduleRoot "native\build\windows\x64\release\DurabilityManager.dll"
$viewSource = Join-Path $moduleRoot "web\dist"
$powerPath = Join-Path $PSScriptRoot "DurabilityManager.esp"
$iniPath = Join-Path $PSScriptRoot "DurabilityManager.ini"
$rulesPath = Join-Path $PSScriptRoot "DurabilityManager.rules.json"

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = (Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json).version
}
foreach ($requiredPath in @($powerPath, $dllPath, $viewSource, $iniPath, $rulesPath)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) { throw "Required build output is missing: $requiredPath" }
}

$pluginDestination = Join-Path $OutputDirectory "Data\SKSE\Plugins"
$viewDestination = Join-Path $OutputDirectory "Data\PrismaUI\views\DurabilityManager"
if (Test-Path -LiteralPath $viewDestination) {
    Remove-Item -LiteralPath $viewDestination -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $pluginDestination, $viewDestination | Out-Null
Copy-Item -LiteralPath $powerPath -Destination (Join-Path $OutputDirectory "Data") -Force
Copy-Item -LiteralPath $dllPath -Destination (Join-Path $pluginDestination "DurabilityManager.dll") -Force
Copy-Item -LiteralPath $iniPath -Destination (Join-Path $pluginDestination "DurabilityManager.ini") -Force
Copy-Item -LiteralPath $rulesPath -Destination (Join-Path $pluginDestination "DurabilityManager.rules.json") -Force
Copy-Item -Path (Join-Path $viewSource "*") -Destination $viewDestination -Recurse -Force
$archivePath = Join-Path $PSScriptRoot ("DurabilityManager-{0}.zip" -f $Version)
Compress-Archive -LiteralPath (Join-Path $OutputDirectory "Data") -DestinationPath $archivePath -Force
Write-Host "Package ready at: $OutputDirectory"
Write-Host "Archive ready at: $archivePath"
