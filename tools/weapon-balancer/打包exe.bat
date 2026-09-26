@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在打包单文件 EXE（需要 pyinstaller：python -m pip install pyinstaller）...
python -m PyInstaller --onefile --noconfirm --clean --name "武器平衡工具" --add-data "web;web" --distpath "dist" --workpath "build_exe" server.py
if errorlevel 1 (
  echo 打包失败。
  pause
  exit /b 1
)
echo.
echo 打包完成：dist\武器平衡工具.exe
set "TOOLS=C:\Users\linos\Desktop\games\+skyrim\TOOLS"
if exist "%TOOLS%" (
  copy /y "dist\武器平衡工具.exe" "%TOOLS%\武器平衡工具.exe" >nul
  echo 已复制到 %TOOLS%\武器平衡工具.exe
)
pause
