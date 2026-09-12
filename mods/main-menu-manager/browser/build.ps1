[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$taskModule = Split-Path $PSScriptRoot -Parent
$taskOutput = Join-Path $taskModule 'build\browser'
$null = New-Item -ItemType Directory -Force -Path $taskOutput
$taskCompiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$taskExe = Join-Path $taskOutput '开屏背景管理器.exe'
& $taskCompiler /nologo /target:winexe /platform:x64 /optimize+ /codepage:65001 /utf8output "/out:$taskExe" ("/win32manifest:" + (Join-Path $PSScriptRoot 'App.manifest')) /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /reference:System.Web.Extensions.dll (Join-Path $PSScriptRoot 'BackgroundBrowser.cs') (Join-Path $PSScriptRoot 'BrowserTests.cs') (Join-Path $PSScriptRoot 'LoadingLibrary.cs') (Join-Path $PSScriptRoot 'LoadingTests.cs')
if ($LASTEXITCODE -ne 0) { throw 'Background browser compilation failed.' }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'App.config') -Destination ($taskExe + '.config') -Force
Write-Output "Built: $taskExe"
