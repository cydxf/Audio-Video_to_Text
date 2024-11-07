@echo off
chcp 65001

echo.
echo 正在启动 Audio-Video2Text ...
echo.
echo 作者：cydxf 
echo github：https://github.com/cydxf
echo Blog：http://cydxf.github.io/
echo. 

rem 设置控制台字体
rem reg add "HKEY_CURRENT_USER\Console" /v "FaceName" /t REG_SZ /d "Consolas" /f

rem 设置Python环境路径
SET PYTHON_PATH=%cd%\env\
rem 设置FFmpeg路径
SET FFMPEG_PATH=%cd%\ffmpeg\bin

echo 正在配置python环境...

rem 设置Python相关环境变量
SET PYTHONPATH=%PYTHON_PATH%
SET PYTHONEXECUTABLE=%PYTHON_PATH%\python.exe
SET PYTHONW_EXECUTABLE=%PYTHON_PATH%\pythonw.exe
SET PYTHON_EXECUTABLE=%PYTHON_PATH%\python.exe
SET PYTHON_BIN_PATH=%PYTHON_EXECUTABLE%
SET PYTHON_LIB_PATH=%PYTHON_PATH%\Lib\site-packages

rem 设置系统路径
SET PATH=%PYTHON_PATH%;%PYTHON_PATH%\Scripts;%FFMPEG_PATH%;%PATH%

echo python 已正确配置

rem 设置Node.js路径（假设nodejs目录与脚本在同级）
SET NODEJS_PATH=%cd%\nodejs

rem 新建临时系统变量NODE_HOME，变量值为nodejs的相对路径
SET NODE_HOME=%cd%\nodejs

rem 更新系统变量Path，临时添加%NODE_HOME%以及node相关的目录
SET PATH=%NODE_HOME%;%NODE_HOME%\npm;%NODE_HOME%\node_modules;%NODE_HOME%\node_cache;%PATH%

rem 设置npm的用户目录为项目所在路径的node_global目录
SET NPM_CONFIG_PREFIX=%cd%\node_global

rem 检查Node.js是否已正确安装
echo 检查 Node.js 是否已安装...
node -v >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Node.js 未检测到，请检测项目文件是否缺失或损坏。
    exit /b
)
echo 已检测到 Node.js 安装。


rem 启动服务器并打开浏览器
echo 启动服务器...
start node server.js


rem 打开默认浏览器并访问服务器地址
echo 正在打开浏览器，访问服务器...
start http://localhost:5501/

pause
