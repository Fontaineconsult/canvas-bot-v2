import click
from dotenv import load_dotenv
from config.yaml_io import read_config
from core.course_root import CanvasCourseRoot
import os

def read_course_list(course_list_file: str):
    """
    Reads a text file containing a list of course IDs
    :param course_list_file: The path to the text file
    :return: A list of course IDs
    """
    with open(course_list_file, 'r') as f:
        course_list = f.read().splitlines()
    return course_list


def detect_valid_env_config():
    """
    Detects if the .env file is present in the network folder and if it contains the required keys
    :return:
    """

    import os
    from os.path import join
    required_env_file_keys = read_config()['required_env_file_keys']
    env_dict = {}
    if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "network", ".env")):
        dotenv_path = join(os.path.join(os.path.dirname(os.path.abspath(__file__)), "network", ".env"))
        with open(dotenv_path, 'r') as f:
            for line in f:
                if line.strip():  # Ignore empty lines
                    key, value = line.strip().split('=', 1)
                    env_dict[key] = value

        load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "network", ".env"))
        return set(required_env_file_keys).issubset(set(list(env_dict.keys())))
    else:
        return False



def collect_env_variables_from_user():
    """
    Collects the required keys from the user
    :return:
    """
    import os
    from os.path import join
    required_env_file_keys = read_config()['required_env_file_keys']
    env_dict = {}
    for key in required_env_file_keys:
        env_dict[key] = input(f"Enter {key}: ")

    dotenv_path = join(os.path.join(os.path.dirname(os.path.abspath(__file__)), "network", ".env"))


    with open(dotenv_path, 'w') as f:
        for key, value in env_dict.items():
            f.write(f"{key}={value}\n")
        os.fsync(f.fileno())

    return dotenv_path



class CanvasBot(CanvasCourseRoot):
    """
    Wraps Canvas Course Root Class
    """
    def __init__(self, course_id: str):
        super().__init__(str(course_id))

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
        self.detect_and_set_env_file_in_network_folder()
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

        def run_bot(ctx,
                    course_id,
                    download_folder,
                    output_as_json,
                    include_video_files=False,
                    include_audio_files=False):

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
