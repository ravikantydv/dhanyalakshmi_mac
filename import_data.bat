@echo off
cd /d "%~dp0"

echo ==========================================
echo   Dhanyalakshmi Insurancewala - CSV Import
echo ==========================================
echo.

python import_csv.py

echo.
echo ==========================================
echo   Finished. Press any key to close.
echo ==========================================
pause