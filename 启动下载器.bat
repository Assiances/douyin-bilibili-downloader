@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 视频下载器 (源码模式)

if exist "%~dp0python_full\python.exe" (
    "%~dp0python_full\python.exe" "%~dp0video_downloader.py"
) else (
    python "%~dp0video_downloader.py"
)

if errorlevel 1 pause