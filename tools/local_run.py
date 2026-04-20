
from canvas_bot import CanvasBot


cpage = [


    28258


]



# for course in range(35000,40000):


bot = CanvasBot(str(21016))
bot.start()
bot.print_content_tree()
print(bot.manifest.content_summary())
print(bot.manifest.resource_summary())

# bot.save_content_as_excel(excel_directory=r"C:\Users\Fonta\PycharmProjects\canvas-bot-v2\test_data\dl")
# bot.clear_folder_contents(directory=r"C:\Users\Fonta\PycharmProjects\canvas-bot-v2\test_data\dl")
# bot.save_content_as_json(json_save_directory=r"C:\Users\913678186\IdeaProjects\canvas-bot-v2",
#                          file_download_directory=r"C:\Users\913678186\IdeaProjects\canvas-bot-v2")