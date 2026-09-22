@echo off
echo ============================================================
echo   Building Winstep Nexus Chinese Fixer Standalone EXE
echo ============================================================

cd /d "%~dp0"

pyinstaller --onefile --windowed ^
    --name "WinstepFixer" ^
    --add-data "Languages;Languages" ^
    --clean ^
    main.py

echo.
if exist "dist\WinstepFixer.exe" (
    echo [SUCCESS] Build succeeded! Executable located at: dist\WinstepFixer.exe
) else (
    echo [ERROR] Build failed!
)
pause
