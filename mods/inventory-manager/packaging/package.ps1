[CmdletBinding()]
param(
    [string]$OutputDirectory = (Join-Path $PSScriptRoot "release")
)

$moduleRoot = Split-Path -Parent $PSScriptRoot
$dllPath = Join-Path $moduleRoot "native\build\windows\x64\release\InventoryManager.dll"
$viewSource = Join-Path $moduleRoot "web\dist"
$iniPath = Join-Path $PSScriptRoot "InventoryManager.ini"

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

Write-Host "Package ready at: $OutputDirectory"
