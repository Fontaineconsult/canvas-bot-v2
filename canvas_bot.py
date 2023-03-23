import click
from core.course_root import CanvasCourseRoot


class CanvasBot(CanvasCourseRoot):
    """
    Wraps Canvas Course Root Class
    """
    def __init__(self, course_id: str):
        super().__init__(str(course_id))

    def start(self):
        self.initialize_course()

    def print_content_tree(self):
        return self.canvas_tree.show_nodes()




if __name__=='__main__':

    @click.command()
    @click.option('--course_id', type=click.STRING, help='The course ID to scrape')
    @click.option('--download_folder', type=click.STRING, help='The Location to Download Files to.'
                                                               ' Default is current directory')
    @click.option('--include_video_files', is_flag=True,
                  help='Include Video Files in Download. Default is False')
    @click.option('--include_audio_files', is_flag=True,
                  help='Include Audio Files in Download. Default is False')
    @click.option('--output_as_json', type=click.STRING,
                  help='Output the content tree as a JSON file. Pass the directory to save the file to.'
                       ' Default is current directory')
    @click.pass_context
    def main(ctx, course_id, download_folder, include_video_files, include_audio_files, output_as_json):
        bot = CanvasBot(course_id)
        bot.start()
        bot.print_content_tree()
        if ctx.params.get('download_folder'):
            flags = (include_video_files, include_audio_files)
            bot.download_files(download_folder, *flags)

        if ctx.params.get('output_as_json'):
            bot.save_content_as_json(output_as_json)

    main()
