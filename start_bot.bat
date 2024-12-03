REM @echo off
REM "C:\Users\hi\anaconda3\python.exe" italian_bot.py
REM pause

@echo off
echo Starting Italian Learning Bot...

:start
echo [%date% %time%] Bot starting... >> bot_startup.log
"C:\Users\hi\anaconda3\python.exe" italian_bot.py
set EXIT_CODE=%errorlevel%
echo [%date% %time%] Bot exited with code %EXIT_CODE% >> bot_startup.log

if %EXIT_CODE% neq 0 (
    echo Bot crashed with error code %EXIT_CODE%
    echo Restarting in 5 seconds...
    echo [%date% %time%] Restarting bot... >> bot_startup.log
    timeout /t 5 /nobreak >nul
    goto start
)

echo Bot stopped normally.
pause