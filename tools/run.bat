
@cd C:\Users\913678186\IdeaProjects\canvas-bot-v2
echo %1
@C:\Users\913678186\IdeaProjects\Canvas-Bot\venv\Scripts\python.exe C:\Users\913678186\IdeaProjects\canvas-bot-v2\tools\run.py %1
@IF %ERRORLEVEL% NEQ 0 PAUSE
