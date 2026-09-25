# 本地构建脚本（本仓库新增，上游没有）。
#
# 用法：pwsh -File build-local.ps1 [-Tests] [-Fresh]
#   -Tests  同时编译平台自带的 60 个测试目标（-DBUILD_TESTING=ON）
#   -Fresh  清理 CMake 配置缓存后重新配置
#
# 两个必须点：必须在 VS x64 工具链环境里构建；且 Developer PowerShell / VsDevCmd 会把
# VCPKG_ROOT 指到 VS 自带的 vcpkg，从而换掉工具链与全部依赖 ABI，所以下面在导入环境之后
# 再把它设回来。
param(
    [switch]$Tests,
    [switch]$Fresh
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$vcpkg = if ($env:VCPKG_ROOT) { $env:VCPKG_ROOT } else { 'C:\Users\linos\Desktop\github\vcpkg' }
$vcvars = 'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'

if (-not (Test-Path -LiteralPath $vcvars)) { throw "找不到 vcvars64.bat：$vcvars" }
if (-not (Test-Path -LiteralPath (Join-Path $vcpkg 'scripts/buildsystems/vcpkg.cmake'))) {
    throw "VCPKG_ROOT 无效（缺 scripts/buildsystems/vcpkg.cmake）：$vcpkg"
}

$dump = cmd /c "`"$vcvars`" >nul && set"
foreach ($line in $dump) {
    $index = $line.IndexOf('=')
    if ($index -le 0) { continue }
    $name = $line.Substring(0, $index)
    $value = $line.Substring($index + 1)
    if ($name -ieq 'PATH') { $env:Path = $value; continue }
    if ($name -ieq 'Path') { continue }
    Set-Item -Path "Env:$name" -Value $value
}
$env:VCPKG_ROOT = $vcpkg

$configureArgs = @('-S', $root, '--preset', 'release', '-DMERIDIAN_ENABLE_SIGNING=OFF', '-DENABLE_LTO=OFF')
$configureArgs += if ($Tests) { '-DBUILD_TESTING=ON' } else { '-DBUILD_TESTING=OFF' }
if ($Fresh) { $configureArgs += '--fresh' }

Write-Host "=== configure（VCPKG_ROOT=$env:VCPKG_ROOT）==="
cmake @configureArgs
if ($LASTEXITCODE -ne 0) { throw "configure 失败：$LASTEXITCODE" }

Write-Host "=== build ==="
cmake --build (Join-Path $root 'build/release') --config Release --parallel 16
if ($LASTEXITCODE -ne 0) { throw "build 失败：$LASTEXITCODE" }

if ($Tests) {
    Write-Host "=== ctest ==="
    ctest --test-dir (Join-Path $root 'build/release') -C Release --output-on-failure --timeout 300 --no-tests=error
    if ($LASTEXITCODE -ne 0) { throw "ctest 失败：$LASTEXITCODE" }
}

$dll = Join-Path $root 'build/release/dist/Release/Data/MeridianUI/MeridianUI.dll'
if (Test-Path -LiteralPath $dll) {
    Write-Host ("=== 产物 ===`n{0}  {1:N0} bytes" -f $dll, (Get-Item -LiteralPath $dll).Length)
} else {
    throw "构建结束但没有找到产物：$dll"
}
