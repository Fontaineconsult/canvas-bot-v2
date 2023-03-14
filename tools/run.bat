
@cd C:\Users\DanielPC\Desktop\Servers\canvas-bot-v2
echo %1
@C:\Users\DanielPC\Desktop\Servers\Canvas-Bot\root\windowsvenv\Scripts\python.exe C:\Users\DanielPC\Desktop\Servers\canvas-bot-v2\tools\run.py %1
@IF %ERRORLEVEL% NEQ 0 PAUSE
