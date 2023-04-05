import sys

def run(course_id):
    bot = CanvasBot(course_id)
    bot.start()

if __name__ == '__main__':

    sys.path.append(r"C:\Users\913678186\IdeaProjects\canvas-bot-v2")
    sys.path.append(r"C:\Users\DanielPC\Desktop\Servers\canvas-bot-v2")
    from canvas_bot import CanvasBot
    run(int(sys.argv[1]))