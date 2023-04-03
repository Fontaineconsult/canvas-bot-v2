#!\windowsvenv\Scripts python
import click, sys, os
from dotenv import load_dotenv
from config.yaml_io import read_config
from core.course_root import CanvasCourseRoot
from network.cred import set_canvas_api_key_to_environment_variable, save_canvas_api_key, save_config_data, \
    load_config_data_from_appdata


def read_course_list(course_list_file: str):
    """
    Reads a text file containing a list of course IDs
    :param course_list_file: The path to the text file
    :return: A list of course IDs
    """
    with open(course_list_file, 'r') as f:
        course_list = f.read().splitlines()
    return course_list


def check_if_api_key_exists():
    if not set_canvas_api_key_to_environment_variable():
        api_key = input("Please enter your Canvas API Key: ")
        save_canvas_api_key(api_key)
        set_canvas_api_key_to_environment_variable()


def load_json_config_file_from_appdata():

    if not load_config_data_from_appdata():

        required_config_file_keys = read_config()['required_env_file_keys']
        app_config_dict = {}

        for key in required_config_file_keys:
            app_config_dict[key] = input(f"Enter {key}: ")
        save_config_data(app_config_dict)
        load_config_data_from_appdata()


class CanvasBot(CanvasCourseRoot):
    """
    Wraps Canvas Course Root Class
    """
    def __init__(self, course_id: str):
        super().__init__(str(course_id))

    def detect_and_set_config(self):
        check_if_api_key_exists()
        load_json_config_file_from_appdata()




    def detect_and_set_env_file_in_network_folder(self):
        """
        Detects if the .env file is present in the network folder and if it contains the required keys
        :return:
        """
        if detect_valid_env_config():

            print("Valid .env file detected")
        else:
            print("No Valid .env file detected")
            path = collect_env_variables_from_user()
            print("setting env variables from .env file")
            load_dotenv(path)


    def start(self):
        print("Starting Canvas Bot")
        self.detect_and_set_config()
        self.initialize_course()

    def print_content_tree(self):
        if self.exists:
            return self.canvas_tree.show_nodes()


if __name__=='__main__':

    @click.command()
    @click.help_option('-h', '--help', help='Welcome to Canvas Bot. This is a simple tool to scrape Canvas courses.'
                                            'It will download all files in a course and organize them into a folder'
                                            ' structure that matches the course structure. It will also output a JSON file of'
                                            ' the course structure. A canvas API key is required to use this tool. Contact your'
                                            ' Canvas administrator for more information.')


    @click.option('--course_id', type=click.STRING, help='The course ID to scrape')
    @click.option('--course_id_list', type=click.STRING, help='Text file containing a list of course IDs to scrape.'
                                                              ' One per line.')
    @click.option('--download_folder', type=click.STRING, help='The Location to download files to.')
    @click.option('--output_as_json', type=click.STRING,
                  help='Output the content tree as a JSON file. Pass the directory to save the file to.')
    @click.option('--include_video_files', is_flag=True,
                  help='Include video files in download. Default is False')
    @click.option('--include_audio_files', is_flag=True,
                  help='Include audio files in download. Default is False')
    @click.option('--include_image_files', is_flag=True,
                  help='Include image files in download. Default is False')
    @click.option('--flatten', is_flag=True,
                  help='Excludes course structure and downloads all files to the same directory. Default is False')
    @click.option('--flush_after_download', is_flag=True,
                  help='Deletes all files after download. Default is False')
    @click.option('--download_hidden_files', is_flag=True,
                  help='Downloads files hidden from students. Default is False')
    @click.option('--show_content_tree', is_flag=True,
                  help='Prints a content tree of the course to the console. Default is False')


    @click.pass_context
    def main(ctx,
             course_id,
             course_id_list,
             download_folder,
             output_as_json,
             include_video_files,
             include_audio_files,
             include_image_files,
             flatten,
             flush_after_download,
             download_hidden_files,
             show_content_tree):

        def run_bot(ctx,
                    course_id,
                    download_folder,
                    output_as_json,
                    include_video_files=False,
                    include_audio_files=False,
                    include_image_files=False,
                    flatten=False,
                    flush_after_download=False,
                    download_hidden_files=False,
                    show_content_tree=False):

            bot = CanvasBot(course_id)
            bot.start()

            if show_content_tree:
                bot.print_content_tree()

            if ctx.params.get('download_folder'):
                flags = (include_video_files,
                         include_audio_files,
                         include_image_files,
                         flatten,
                         flush_after_download,
                         download_hidden_files)

                bot.download_files(download_folder, *flags)

            if ctx.params.get('output_as_json'):
                bot.save_content_as_json(output_as_json)

        if course_id_list:
            course_list = read_course_list(course_id_list)
            for course_id in course_list:
                run_bot(ctx,
                        course_id,
                        download_folder,
                        output_as_json,
                        include_video_files,
                        include_audio_files,
                        include_image_files,
                        flatten,
                        flush_after_download,
                        download_hidden_files,
                        show_content_tree)

        if course_id:
            run_bot(ctx,
                    course_id,
                    download_folder,
                    output_as_json,
                    include_video_files,
                    include_audio_files,
                    include_image_files,
                    flatten,
                    flush_after_download,
                    download_hidden_files,
                    show_content_tree)

    main()
