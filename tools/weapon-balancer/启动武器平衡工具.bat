@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在读取 MO2 载入顺序（首次约 4 秒，之后走缓存）...
echo 浏览器会自动打开工具页面；关闭这个窗口即可停止工具。
echo.
python server.py
if errorlevel 1 (
  echo.
  echo 启动失败。请确认已安装 Python，或端口被占用时改用：python server.py --port 8754
)
pause
