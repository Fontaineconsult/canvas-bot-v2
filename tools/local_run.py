
from canvas_bot import CanvasBot


cpage = [


    28258


]



for course in range(35000,40000):


    bot = CanvasBot(str(course))
    bot.start()
    bot.print_content_tree()
    bot.download_files(
        directory=r"C:\Users\Fonta\PycharmProjects\canvas-bot-v2\test_data\dl",
        include_video_files=True,
        include_audio_files=True
    )
    bot.clear_folder_contents(directory=r"C:\Users\Fonta\PycharmProjects\canvas-bot-v2\test_data\dl")
    # bot.save_content_as_json(json_save_directory=r"C:\Users\913678186\IdeaProjects\canvas-bot-v2",
    #                          file_download_directory=r"C:\Users\913678186\IdeaProjects\canvas-bot-v2")