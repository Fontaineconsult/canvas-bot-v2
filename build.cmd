windowsvenv\Scripts\activate && ^
pyinstaller --onefile --name canvas_bot --console --add-data "config\config.yaml;config\." ^
--add-data "config\download_manifest.yaml;config\." --add-data "config\re.yaml;config\." ^
--paths "C:\Users\DanielPC\Desktop\Servers\canvas-bot-v2" ^
--paths "C:\Users\DanielPC\Desktop\Servers\canvas-bot-v2\config" canvas_bot.py