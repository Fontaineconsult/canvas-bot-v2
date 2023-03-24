import click
from core.course_root import CanvasCourseRoot

def read_course_list(course_list_file: str):
    """
    Reads a text file containing a list of course IDs
    :param course_list_file: The path to the text file
    :return: A list of course IDs
    """
    with open(course_list_file, 'r') as f:
        course_list = f.read().splitlines()
    return course_list



class CanvasBot(CanvasCourseRoot):
    """
    Wraps Canvas Course Root Class
    """
    def __init__(self, course_id: str):
        super().__init__(str(course_id))

    def start(self):
        self.initialize_course()

    def print_content_tree(self):
        if self.exists:
            return self.canvas_tree.show_nodes()

if __name__=='__main__':

    @click.command()
    @click.option('--course_id', type=click.STRING, help='The course ID to scrape')
    @click.option('--course_id_list', type=click.STRING, help='Text file containing a list of course IDs to scrape.'
                                                              ' One per line.')
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
    def main(ctx, course_id, course_id_list, download_folder, output_as_json, include_video_files, include_audio_files):


        def run_bot(ctx, course_id, download_folder, output_as_json, include_video_files=False, include_audio_files=False):

            bot = CanvasBot(course_id)
            bot.start()
            bot.print_content_tree()
            if ctx.params.get('download_folder'):
                flags = (include_video_files, include_audio_files)
                bot.download_files(download_folder, *flags)

            if ctx.params.get('output_as_json'):
                bot.save_content_as_json(output_as_json)


        if course_id_list:
            course_list = read_course_list(course_id_list)
            for course_id in course_list:
                run_bot(ctx, course_id, download_folder, output_as_json, include_video_files, include_audio_files)


        if course_id:
            run_bot(ctx, course_id, download_folder, output_as_json, include_video_files, include_audio_files)



    main()
