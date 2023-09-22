#!\windowsvenv\Scripts python
import click, sys, logging
from config.yaml_io import read_config
from core.course_root import CanvasCourseRoot
from network.cred import set_canvas_api_key_to_environment_variable, save_canvas_api_key, save_config_data, \
    load_config_data_from_appdata, delete_canvas_api_key, delete_config_file_from_appdata, \
    save_canvas_studio_client_keys, save_canvas_studio_tokens, get_canvas_studio_tokens, \
    set_canvas_studio_api_key_to_environment_variable
from network.studio_api import authorize_studio_token, refresh_studio_token

version = read_config()['version']
import tools.logger
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


def configure_canvas_studio_api_key():

    token, reauth = get_canvas_studio_tokens()
    if token and reauth:

        print("Canvas Studio API tokens found")
        token, reauth = refresh_studio_token(reauth)
        save_canvas_studio_tokens(token, reauth)
        set_canvas_studio_api_key_to_environment_variable()
        return

    client_id = input("Enter your Canvas Studio Client ID (enter nothing to skip): ")

    if client_id:
        client_secret = input("Enter your Canvas Studio Client Secret: ")
        callback_url = input("Enter your Canvas Studio Callback URL: ")

        if client_id and client_secret and callback_url:
            save_canvas_studio_client_keys(client_id, client_secret)
            canvas_studio_config_keys = read_config()['canvas_studio_config_keys']
            canvas_studio_config_dict = {}
            for key in canvas_studio_config_keys:

                canvas_studio_config_dict[key] = input(f"Enter {key}: ")

            save_config_data(canvas_studio_config_dict)

            token, re_auth_token = authorize_studio_token()

            if token and re_auth_token:
                save_canvas_studio_tokens(token, re_auth_token)
    else:
        print("Skipping Canvas Studio API Key Configuration. Canvas Studio access will not be available")


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
        configure_canvas_studio_api_key()

    def reset_config(self):
        print("Resetting Access Token and Config File")
        delete_canvas_api_key()
        delete_config_file_from_appdata()
        self.detect_and_set_config()

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
    @click.option('--reset_params', is_flag=True,
                  help='Resets Access Token and config file. Default is False')
    @click.option('--output_as_excel', type=click.STRING,
                  help='The location to export the course content as an excel file.')
    @click.option('--check_video_site_caption_status', is_flag=True,
                  help='Where available, checks the if YouTube or Vimeo videos contain captions. Default is False')

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
             reset_params,
             check_video_site_caption_status
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
            "reset_params": reset_params,
            "check_video_site_caption_status": check_video_site_caption_status,

        }

        def run_bot(ctx,
                    course_id,
                    **params
                    ):

            bot = CanvasBot(course_id)

            if reset_params:
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

        if reset_params and not course_id:
            bot = CanvasBot()
            bot.reset_config()
            print("No course ID provided. Exiting")
            sys.exit()


    try:
        main()
    except Exception as exc:
        log.exception(exc)
        raise exc


