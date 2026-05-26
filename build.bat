@echo off
echo Building Cashy portable...
pyinstaller cashy.spec --noconfirm --clean
echo.
echo Done! Portable app is in dist\Cashy\
pause
