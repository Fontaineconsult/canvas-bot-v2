#!\windowsvenv\Scripts python
import os

import click, sys, logging
from config.yaml_io import read_config
from core.course_root import CanvasCourseRoot
from network.cred import set_canvas_api_key_to_environment_variable, save_canvas_api_key, load_config_data_from_appdata, delete_canvas_api_key, delete_config_file_from_appdata, \
    save_canvas_studio_client_keys, get_canvas_studio_tokens, \
    set_canvas_studio_api_key_to_environment_variable, delete_canvas_studio_client_keys, delete_canvas_studio_tokens
from network.set_config import save_config_data
from network.studio_api import authorize_studio_token, refresh_studio_token
from tools.canvas_studio_caption_upload import add_caption_to_canvas_studio_video

version = read_config()['version']
log = logging.getLogger(__name__)


def read_course_list(course_list_file: str):
    """
    Reads a text file containing a list of course IDs
    :param course_list_file: The path to the text file
    :return: A list of course IDs
    """
    with open(course_list_file, 'r') as f:
        course_list = [line.strip() for line in f]
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


def configure_canvas_studio_api_key(force_studio_config=True):

    """
    refreshes saved tokens if they exist. If not, prompts user to authorize and save tokens.
     Sets new tokens to env variables
    :return:
    """

    if os.environ['studio_enabled'] == 'True':

        token, re_auth = get_canvas_studio_tokens()

        if token and re_auth:
            token, re_auth = refresh_studio_token(re_auth)
            set_canvas_studio_api_key_to_environment_variable(token, re_auth)
        else:
            print("Canvas Studio Enabled but no tokens found.")
            # Collect client ID and Client Secret and Save them
            set_canvas_studio_config(force_studio_config)
            # get new tokens using client ID and Client Secret
            token, re_auth = authorize_studio_token()

            if token and re_auth:
                set_canvas_studio_api_key_to_environment_variable(token, re_auth)

    else:
        print("Canvas Studio Integration Disabled")


def set_canvas_studio_config(force_config=False):

    """
    saves canvas studio client keys to env variables
    :param force_config:
    :return:
    """

    def config_input():
        while True:
            response = input("Would you like to enable the canvas studio integration?").strip().lower()
            if response == "yes":

                canvas_studio_config_keys = read_config()['canvas_studio_config_keys']
                canvas_studio_config_dict = {}

                client_id = input("Enter your Canvas Studio Client ID: ")
                client_secret = input("Enter your Canvas Studio Client Secret: ")

                if client_id and client_secret:
                    print("saving client keys")
                    save_canvas_studio_client_keys(client_id, client_secret)

                for key in canvas_studio_config_keys:
                    canvas_studio_config_dict[key] = input(f"Enter {key}: ")

                canvas_studio_config_dict['studio_enabled'] = True
                save_config_data(canvas_studio_config_dict)
                load_json_config_file_from_appdata()
                return True

            elif response == "no":
                save_config_data({'studio_enabled': False})
                return False
            else:
                print("Invalid input. Please enter 'Yes' or 'No'.")



    try:
        if os.environ['studio_enabled'] == 'True' and force_config is False:
            configure_canvas_studio_api_key()
            return

        if os.environ['studio_enabled'] == 'False' and force_config is False:
            return
    except KeyError:
        config_input()
    config_input()




class CanvasBot(CanvasCourseRoot):
    """
    Wraps Canvas Course Root Class
    """
    def __init__(self, course_id=None):
        if course_id:
            self.detect_and_set_config()
            super().__init__(str(course_id))

    def detect_and_set_config(self):
        print("Detecting Access Token and Config File")
        check_if_api_key_exists()
        load_json_config_file_from_appdata()
        set_canvas_studio_config()


    def reset_config(self):
        print("Resetting Access Token and Config File")
        delete_canvas_api_key()
        delete_config_file_from_appdata()
        self.detect_and_set_config()


    def reset_canvas_studio_config(self):
        print("Resetting Canvas Studio Config")
        delete_canvas_studio_client_keys()
        delete_canvas_studio_tokens()
        set_canvas_studio_config(force_config=True)


    def start(self):
        print(f"Starting Canvas Bot - {version} ")
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
    @click.option('--course_id_list', type=click.STRING, help='Text file containing a list'
                                                              ' of course IDs to scrape.'
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
    @click.option('--reset_canvas_params', is_flag=True,
                  help='Resets Access Tokens and config file. Default is False')
    @click.option('--reset_canvas_studio_params', is_flag=True,
                  help='Resets config variables for canvas studio. Default is False')
    @click.option('--output_as_excel', type=click.STRING,
                  help='The location to export the course content as an excel file.')
    @click.option('--check_video_site_caption_status', is_flag=True,
                  help='Where available, checks the if YouTube or Vimeo videos contain captions. Default is False')
    @click.option('--caption_file_location', type=click.STRING,
                  help='Pass the location of a caption file to upload to Canvas Studio.'
                       ' Must also include the canvas studio media id "--media_id" flag')
    @click.option('--canvas_studio_media_id', type=click.STRING,
                  help='Pass the Canvas Studio media ID of the item to add a caption file to.'
                       'Must also include the "--caption_file_location" flag')

    @click.pass_context
    def main(ctx,
             course_id,
             course_id_list,
             download_folder,
             output_as_json,
             output_as_excel,
             include_video_files,
             include_audio_files,
             include_image_files,
             flatten,
             flush_after_download,
             download_hidden_files,
             show_content_tree,
             reset_canvas_params,
             reset_canvas_studio_params,
             check_video_site_caption_status,
             caption_file_location,
             canvas_studio_media_id
             ):

        params = {

            "download_folder": download_folder,
            "output_as_json": output_as_json,
            "output_as_excel": output_as_excel,
            "include_video_files": include_video_files,
            "include_audio_files": include_audio_files,
            "include_image_files": include_image_files,
            "flatten": flatten,
            "flush_after_download": flush_after_download,
            "download_hidden_files": download_hidden_files,
            "show_content_tree": show_content_tree,
            "reset_params": reset_canvas_params,
            "check_video_site_caption_status": check_video_site_caption_status,
            "reset_canvas_studio_params": reset_canvas_studio_params,
            "caption_file_location": caption_file_location,
            "canvas_studio_media_id": canvas_studio_media_id

        }

        def run_bot(ctx,
                    course_id,
                    **params
                    ):

            bot = CanvasBot(course_id)

            if ctx.params.get('caption_file_location') or ctx.params.get('canvas_studio_media_id'):

                if caption_file_location and canvas_studio_media_id:
                    add_caption_to_canvas_studio_video(course_id,
                                                       params['caption_file_location'],
                                                       params['canvas_studio_media_id'])
                    sys.exit()

                else:
                    click.echo("Must include both caption file location and canvas studio media id")
                    input()
                    sys.exit()

            if reset_canvas_params:
                bot.reset_config()

            if reset_canvas_params:
                bot.reset_config()


            if course_id:
                bot.start()
            else:
                print("No course ID provided. Exiting")
                sys.exit()

            if show_content_tree:
                bot.print_content_tree()

            if ctx.params.get('download_folder'):
                bot.download_files(download_folder, **params)

            if ctx.params.get('output_as_json'):
                bot.save_content_as_json(output_as_json, download_folder, **params)

            if ctx.params.get('output_as_excel'):
                bot.save_content_as_excel(output_as_excel, **params)




        if course_id_list:
            course_list = read_course_list(course_id_list)
            for course_id in course_list:
                run_bot(ctx,
                        course_id,
                        **params)

        if course_id:
            run_bot(ctx,
                    course_id,
                    **params)

        if reset_canvas_params and not course_id:
            bot = CanvasBot()
            bot.reset_config()
            print("No course ID provided. Exiting")
            sys.exit()


    try:
        main()
    except Exception as exc:
        log.exception(exc)
        raise exc


