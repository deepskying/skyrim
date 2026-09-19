[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$moduleRoot = Split-Path -Parent $PSScriptRoot
$version = (Get-Content -LiteralPath (Join-Path $moduleRoot 'web/package.json') -Raw | ConvertFrom-Json).version
if ($version -notmatch '^\d+\.\d+\.\d+$') { throw 'Invalid package version' }
$dll = Join-Path $moduleRoot 'native/build/windows/x64/release/CompanionManager.dll'
$web = Join-Path $moduleRoot 'web/dist'
foreach ($required in @($dll, (Join-Path $web 'index.html'), (Join-Path $moduleRoot 'data/CompanionManager.esp'), (Join-Path $moduleRoot 'data/Scripts/CMController.pex'))) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Build output missing: $required" }
}
foreach ($script in @('CMDialogue', 'CMRandomOutfitTopic')) {
    if (-not (Test-Path -LiteralPath (Join-Path $moduleRoot "data/Scripts/$script.pex") -PathType Leaf)) { throw "Dialogue script missing: $script" }
}
if (-not (Test-Path -LiteralPath (Join-Path $moduleRoot 'data/SEQ/CompanionManager.seq') -PathType Leaf)) { throw 'Dialogue startup index missing' }
$release = Join-Path $PSScriptRoot 'release'
$name = "CompanionManager-$version-fulltest-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
$stage = Join-Path $release $name
if (Test-Path -LiteralPath $stage) { throw "Output already exists: $stage" }
$plugins = Join-Path $stage 'SKSE/Plugins'
$view = Join-Path $stage 'MeridianUI/companion-manager'
New-Item -ItemType Directory -Path $plugins, $view -Force | Out-Null
Copy-Item -LiteralPath $dll -Destination $plugins
Copy-Item -Path (Join-Path $web '*') -Destination $view -Recurse
Copy-Item -LiteralPath (Join-Path $moduleRoot 'data/CompanionManager.esp') -Destination $stage
Copy-Item -LiteralPath (Join-Path $moduleRoot 'data/Scripts') -Destination $stage -Recurse
Copy-Item -LiteralPath (Join-Path $moduleRoot 'data/SEQ') -Destination $stage -Recurse
Copy-Item -LiteralPath (Join-Path $moduleRoot 'README.md') -Destination $stage
Copy-Item -LiteralPath (Join-Path $moduleRoot 'native/vendor/MeridianUIAPI/LICENSE-MIT') -Destination (Join-Path $stage 'Meridian-SDK-LICENSE.txt')
$files = @(Get-ChildItem -LiteralPath $stage -File -Recurse | ForEach-Object {
    [ordered]@{ path = [IO.Path]::GetRelativePath($stage, $_.FullName).Replace('\','/'); sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash }
})
[ordered]@{ version = $version; stage = 'fulltest'; files = $files } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $stage 'manifest.json') -Encoding utf8
$zip = "$stage.zip"
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zip
Write-Output "MO2 package: $zip"
Write-Output "No MO2 profile or existing mod has been modified."
