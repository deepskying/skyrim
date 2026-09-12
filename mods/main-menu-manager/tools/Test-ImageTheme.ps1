$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$taskModule = Split-Path $PSScriptRoot -Parent
$taskBase = [IO.Path]::GetFullPath((Join-Path $taskModule 'build\image-tests'))
$taskRoot = Join-Path $taskBase ([Guid]::NewGuid().ToString('N'))
$taskTemplate = Join-Path $taskRoot '模板'
$taskOutput = Join-Path $taskRoot '极光之夜'
$taskImage = Join-Path $taskRoot '我的背景.png'
$taskWallpaperRelative = 'Data\textures\interface\objects\mainmenuwallpaper.dds'
$taskLogoRelative = 'Data\meshes\interface\logo\logo.nif'
$taskChecks = 0
function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
    $script:taskChecks++
}
function Assert-Fails([scriptblock]$Action, [string]$Message) {
    $taskFailed = $false
    try { & $Action | Out-Null } catch { $taskFailed = $true }
    Assert-True $taskFailed $Message
}
try {
    foreach ($taskRelative in @($taskWallpaperRelative, $taskLogoRelative, 'Data\SKSE\Plugins\ignored.dll')) {
        $null = New-Item -ItemType Directory -Force -Path (Split-Path (Join-Path $taskTemplate $taskRelative) -Parent)
    }
    $taskHeader = New-Object byte[] 160
    [Text.Encoding]::ASCII.GetBytes('DDS ').CopyTo($taskHeader, 0)
    [BitConverter]::GetBytes([uint32]124).CopyTo($taskHeader, 4)
    [BitConverter]::GetBytes([uint32]2).CopyTo($taskHeader, 12)
    [BitConverter]::GetBytes([uint32]4).CopyTo($taskHeader, 16)
    [IO.File]::WriteAllBytes((Join-Path $taskTemplate $taskWallpaperRelative), $taskHeader)
    [IO.File]::WriteAllText((Join-Path $taskTemplate $taskLogoRelative), "Gamebryo File Format, Version 20.2.0.7`ntextures\interface\objects\mainmenuwallpaper.dds")
    [IO.File]::WriteAllText((Join-Path $taskTemplate 'Data\SKSE\Plugins\ignored.dll'), 'do not copy')
    $taskBefore = (Get-FileHash -LiteralPath (Join-Path $taskTemplate $taskWallpaperRelative)).Hash
    $taskBitmap = [Drawing.Bitmap]::new(8, 8)
    try {
        for ($taskY = 0; $taskY -lt 8; $taskY++) {
            $taskColor = if ($taskY -lt 2) { [Drawing.Color]::Lime } elseif ($taskY -lt 4) { [Drawing.Color]::Red } elseif ($taskY -lt 6) { [Drawing.Color]::Blue } else { [Drawing.Color]::Yellow }
            for ($taskX = 0; $taskX -lt 8; $taskX++) { $taskBitmap.SetPixel($taskX, $taskY, $taskColor) }
        }
        $taskBitmap.Save($taskImage, [Drawing.Imaging.ImageFormat]::Png)
    } finally { $taskBitmap.Dispose() }
    & (Join-Path $PSScriptRoot 'New-ImageTheme.ps1') -ImagePath $taskImage -TemplateDirectory $taskTemplate -OutputDirectory $taskOutput -Name '极光' | Out-Null
    $taskDds = [IO.File]::ReadAllBytes((Join-Path $taskOutput $taskWallpaperRelative))
    Assert-True ($taskDds.Length -eq (128 + 4 * 2 * 4)) 'DDS header and pixel byte count'
    Assert-True ([Text.Encoding]::ASCII.GetString($taskDds, 0, 4) -eq 'DDS ') 'DDS signature'
    Assert-True ([BitConverter]::ToUInt32($taskDds, 16) -eq 4 -and [BitConverter]::ToUInt32($taskDds, 12) -eq 2) 'Template dimensions'
    Assert-True ([BitConverter]::ToUInt32($taskDds, 88) -eq 32 -and [BitConverter]::ToUInt32($taskDds, 92) -eq 0x00FF0000) 'BGRA channel format'
    Assert-True ($taskDds[130] -gt $taskDds[128] -and $taskDds[144] -gt $taskDds[146]) 'Center crop and row orientation preserve red top / blue bottom'
    Assert-True ($taskDds[131] -eq 255 -and $taskDds[147] -eq 255) 'Opaque alpha'
    Assert-True (Test-Path -LiteralPath (Join-Path $taskOutput 'preview.jpg')) 'Preview generated'
    Assert-True (-not (Test-Path -LiteralPath (Join-Path $taskOutput 'disabled.txt'))) 'Completed theme enabled'
    Assert-True (-not (Test-Path -LiteralPath (Join-Path $taskOutput 'Data\SKSE'))) 'Ignore DLLs and scripts'
    $taskMetadata = [IO.File]::ReadAllText((Join-Path $taskOutput 'theme.json')) | ConvertFrom-Json
    Assert-True ($taskMetadata.name -eq '极光' -and $taskMetadata.enabled) 'UTF-8 metadata'
    Assert-True ((Get-FileHash -LiteralPath (Join-Path $taskTemplate $taskWallpaperRelative)).Hash -eq $taskBefore) 'Template stays unchanged'
    $taskGeneratedHash = (Get-FileHash -LiteralPath (Join-Path $taskOutput $taskWallpaperRelative)).Hash
    Assert-Fails { & (Join-Path $PSScriptRoot 'New-ImageTheme.ps1') -ImagePath $taskImage -TemplateDirectory $taskTemplate -OutputDirectory $taskOutput } 'Reject overwriting a theme'
    Assert-True ((Get-FileHash -LiteralPath (Join-Path $taskOutput $taskWallpaperRelative)).Hash -eq $taskGeneratedHash) 'Existing theme preserved'
    $taskBroken = Join-Path $taskRoot 'broken.png'; [IO.File]::WriteAllText($taskBroken, 'invalid PNG')
    Assert-Fails { & (Join-Path $PSScriptRoot 'New-ImageTheme.ps1') -ImagePath $taskBroken -TemplateDirectory $taskTemplate -OutputDirectory (Join-Path $taskRoot 'incomplete') } 'Broken image fails'
    Assert-True (Test-Path -LiteralPath (Join-Path $taskRoot 'incomplete\disabled.txt')) 'Incomplete import excluded from random pool'
    Write-Output "PASS: $taskChecks image import checks"
} finally {
    # Verify the absolute recursive-delete target is our GUID fixture only.
    $taskResolved = [IO.Path]::GetFullPath($taskRoot)
    if ([IO.Path]::GetDirectoryName($taskResolved) -ne $taskBase -or [IO.Path]::GetFileName($taskResolved) -notmatch '^[a-f0-9]{32}$') {
        throw 'Refusing to clean an unexpected test directory.'
    }
    if (Test-Path -LiteralPath $taskResolved) { Remove-Item -LiteralPath $taskResolved -Recurse -Force }
}
