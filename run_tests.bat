@echo off
setlocal

cd /d "%~dp0"
uv run --locked python -m unittest discover --verbose
