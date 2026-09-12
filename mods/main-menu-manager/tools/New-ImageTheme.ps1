[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$ImagePath,
    [Parameter(Mandatory)][string]$TemplateDirectory,
    [Parameter(Mandatory)][string]$OutputDirectory,
    [string]$Name
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

# Offline authoring helper. It only creates a new theme directory. The supplied
# template remains unchanged, and no live game Data path is inferred or written.
$taskImagePath = (Resolve-Path -LiteralPath $ImagePath).Path
$taskTemplate = (Resolve-Path -LiteralPath $TemplateDirectory).Path
$taskOutput = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $taskOutput) { throw 'OutputDirectory already exists; choose a new theme folder.' }
if ([IO.Path]::GetExtension($taskImagePath).ToLowerInvariant() -notin @('.png', '.jpg', '.jpeg', '.bmp')) {
    throw 'ImagePath must be PNG, JPG, JPEG or BMP.'
}
$taskData = Join-Path $taskTemplate 'Data'
$taskWallpaper = Join-Path $taskData 'textures\interface\objects\mainmenuwallpaper.dds'
$taskLogo = Join-Path $taskData 'meshes\interface\logo\logo.nif'
foreach ($taskRequired in @($taskData, $taskWallpaper, $taskLogo)) {
    if (-not (Test-Path -LiteralPath $taskRequired)) { throw "Template is missing: $taskRequired" }
}
$taskLogoText = [Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($taskLogo)).ToLowerInvariant().Replace('/', '\')
if (-not $taskLogoText.Contains('interface\objects\mainmenuwallpaper.dds')) {
    throw 'This helper needs a template whose logo.nif references interface\objects\mainmenuwallpaper.dds.'
}
if ($taskOutput.StartsWith($taskTemplate.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'OutputDirectory must be outside the template.'
}

# Read only the DDS header; use the template dimensions to preserve its aspect
# ratio. Generated images are center-cropped, never stretched.
$taskReader = [IO.BinaryReader]::new([IO.File]::OpenRead($taskWallpaper))
try {
    if ([Text.Encoding]::ASCII.GetString($taskReader.ReadBytes(4)) -ne 'DDS ' -or $taskReader.ReadUInt32() -ne 124) {
        throw 'Template wallpaper is not a valid DDS.'
    }
    $null = $taskReader.ReadUInt32()
    $taskHeight = [int]$taskReader.ReadUInt32()
    $taskWidth = [int]$taskReader.ReadUInt32()
} finally { $taskReader.Dispose() }
if ($taskWidth -lt 1 -or $taskHeight -lt 1 -or $taskWidth -gt 8192 -or $taskHeight -gt 8192) {
    throw 'Template dimensions must be between 1 and 8192 pixels.'
}

function Assert-NoLinks([string]$Path) {
    $taskInspect = [IO.Path]::GetFullPath($Path)
    while ($taskInspect) {
        if (Test-Path -LiteralPath $taskInspect) {
            if ((Get-Item -LiteralPath $taskInspect -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw "Linked paths are not supported: $taskInspect"
            }
        }
        $taskInspect = [IO.Path]::GetDirectoryName($taskInspect)
    }
}
Assert-NoLinks $taskData
Assert-NoLinks $taskOutput
$taskResources = @(Get-ChildItem -LiteralPath $taskData -Recurse -Force)
foreach ($taskResource in $taskResources) { Assert-NoLinks $taskResource.FullName }

$null = New-Item -ItemType Directory -Path $taskOutput
$taskDisabled = Join-Path $taskOutput 'disabled.txt'
[IO.File]::WriteAllText($taskDisabled, 'Import is incomplete. Do not enable until it succeeds.')
foreach ($taskResource in $taskResources) {
    if ($taskResource.PSIsContainer) { continue }
    $taskRelative = $taskResource.FullName.Substring($taskData.TrimEnd('\').Length + 1).Replace('\', '/')
    if ($taskRelative -notmatch '^(textures/.+\.dds|meshes/interface/logo/logo(01ae)?\.nif|meshes/interface/intmenufogparticles\.nif|music/special/mus_maintheme\.(xwm|wav))$') { continue }
    $taskDestination = Join-Path (Join-Path $taskOutput 'Data') $taskRelative
    $null = New-Item -ItemType Directory -Force -Path (Split-Path $taskDestination -Parent)
    Copy-Item -LiteralPath $taskResource.FullName -Destination $taskDestination
}

$taskSource = $null
$taskBitmap = $null
$taskGraphics = $null
$taskPixels = $null
try {
    $taskSource = [Drawing.Image]::FromFile($taskImagePath)
    $taskBitmap = [Drawing.Bitmap]::new($taskWidth, $taskHeight, [Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $taskGraphics = [Drawing.Graphics]::FromImage($taskBitmap)
    $taskGraphics.Clear([Drawing.Color]::Black)
    $taskGraphics.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $taskGraphics.PixelOffsetMode = [Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $taskScale = [Math]::Max($taskWidth / [double]$taskSource.Width, $taskHeight / [double]$taskSource.Height)
    $taskCropWidth = $taskWidth / $taskScale
    $taskCropHeight = $taskHeight / $taskScale
    $taskSourceRect = [Drawing.RectangleF]::new(
        [single](($taskSource.Width - $taskCropWidth) / 2), [single](($taskSource.Height - $taskCropHeight) / 2),
        [single]$taskCropWidth, [single]$taskCropHeight)
    $taskGraphics.DrawImage($taskSource, [Drawing.RectangleF]::new(0, 0, $taskWidth, $taskHeight), $taskSourceRect, [Drawing.GraphicsUnit]::Pixel)
    $taskGraphics.Dispose(); $taskGraphics = $null

    $taskNewWallpaper = Join-Path $taskOutput 'Data\textures\interface\objects\mainmenuwallpaper.dds'
    $taskWriter = [IO.BinaryWriter]::new([IO.File]::Open($taskNewWallpaper, [IO.FileMode]::Create))
    try {
        $taskWriter.Write([Text.Encoding]::ASCII.GetBytes('DDS '))
        # Legacy DDS header for uncompressed B8G8R8A8. One mip is appropriate for
        # a fixed main-menu wallpaper; no external texture converter is needed.
        foreach ($taskValue in @([uint32]124, [uint32]0x100F, [uint32]$taskHeight, [uint32]$taskWidth, [uint32]($taskWidth * 4), [uint32]0, [uint32]0)) {
            $taskWriter.Write([uint32]$taskValue)
        }
        for ($taskI = 0; $taskI -lt 11; $taskI++) { $taskWriter.Write([uint32]0) }
        foreach ($taskValue in @([uint32]32, [uint32]0x41, [uint32]0, [uint32]32, [uint32]0x00FF0000, [uint32]0x0000FF00, [uint32]0x000000FF, [uint32]::Parse('FF000000', [Globalization.NumberStyles]::HexNumber), [uint32]0x1000, [uint32]0, [uint32]0, [uint32]0, [uint32]0)) {
            $taskWriter.Write([uint32]$taskValue)
        }
        $taskPixels = $taskBitmap.LockBits([Drawing.Rectangle]::new(0, 0, $taskWidth, $taskHeight), [Drawing.Imaging.ImageLockMode]::ReadOnly, [Drawing.Imaging.PixelFormat]::Format32bppArgb)
        $taskRow = New-Object byte[] ($taskWidth * 4)
        for ($taskY = 0; $taskY -lt $taskHeight; $taskY++) {
            [Runtime.InteropServices.Marshal]::Copy([IntPtr]::Add($taskPixels.Scan0, $taskY * $taskPixels.Stride), $taskRow, 0, $taskRow.Length)
            $taskWriter.Write($taskRow)
        }
        $taskBitmap.UnlockBits($taskPixels); $taskPixels = $null
    } finally { $taskWriter.Dispose() }
    $taskPreviewWidth = [Math]::Min(640, $taskWidth)
    $taskPreviewHeight = [Math]::Max(1, [int]($taskHeight * $taskPreviewWidth / $taskWidth))
    $taskPreview = [Drawing.Bitmap]::new($taskBitmap, [Drawing.Size]::new($taskPreviewWidth, $taskPreviewHeight))
    try { $taskPreview.Save((Join-Path $taskOutput 'preview.jpg'), [Drawing.Imaging.ImageFormat]::Jpeg) }
    finally { $taskPreview.Dispose() }
} finally {
    if ($taskPixels) { $taskBitmap.UnlockBits($taskPixels) }
    if ($taskGraphics) { $taskGraphics.Dispose() }
    if ($taskBitmap) { $taskBitmap.Dispose() }
    if ($taskSource) { $taskSource.Dispose() }
}
if (-not $Name) { $Name = Split-Path $taskOutput -Leaf }
$taskMetadata = @{ name = $Name; enabled = $true; template = (Split-Path $taskTemplate -Leaf); image = [IO.Path]::GetFileName($taskImagePath) } | ConvertTo-Json
[IO.File]::WriteAllText((Join-Path $taskOutput 'theme.json'), $taskMetadata, [Text.UTF8Encoding]::new($false))
Remove-Item -LiteralPath $taskDisabled
Write-Output "Created theme: $taskOutput"
Write-Output "Wallpaper: $taskWidth x $taskHeight, center crop; template models/effects/music retained."
