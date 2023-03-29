windowsvenv\Scripts\activate && ^
pyinstaller --onefile --name canvas_bot --console --add-data "config\config.yaml;config\." ^
--add-data "config\download_manifest.yaml;config\." --add-data "config\re.yaml;config\." ^
--paths "%~dp0" ^
--paths "%~dp0config" canvas_bot.py