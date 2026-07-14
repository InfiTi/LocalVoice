@echo off
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d E:\AI\LocalVoice
.venv\Scripts\pythonw.exe gui.py
