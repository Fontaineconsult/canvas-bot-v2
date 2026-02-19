#!\windowsvenv\Scripts python
import os

import click, sys, logging
import re
from config.yaml_io import read_re, write_re, reset_re
from core.course_root import CanvasCourseRoot
from network.cred import set_canvas_api_key_to_environment_variable, save_canvas_api_key, load_config_data_from_appdata, delete_canvas_api_key, delete_config_file_from_appdata, \
    save_canvas_studio_client_keys, get_canvas_studio_tokens, \
    set_canvas_studio_api_key_to_environment_variable, delete_canvas_studio_client_keys, delete_canvas_studio_tokens
from network.set_config import save_config_data
from network.studio_api import authorize_studio_token, refresh_studio_token
from tools.canvas_studio_caption_upload import add_caption_to_canvas_studio_video

__version__ = "1.2.0"
version = __version__
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
    """Check if Canvas API key exists, prompt user if not."""
    if not set_canvas_api_key_to_environment_variable():
        print("\n" + "=" * 50)
        print("Canvas API Access Token Required")
        print("=" * 50)
        print("\nTo get an access token:")
        print("  1. Log into Canvas")
        print("  2. Go to Account > Settings")
        print("  3. Scroll to 'Approved Integrations'")
        print("  4. Click '+ New Access Token'")
        print("  5. Copy the generated token\n")

        api_key = input("Paste your Canvas API Access Token: ").strip()
        if api_key:
            save_canvas_api_key(api_key)
            set_canvas_api_key_to_environment_variable()
            print("[OK] Access token saved securely.\n")
        else:
            print("[ERROR] No token provided. Exiting.")
            sys.exit(1)


def _prompt_with_default(prompt, default=None):
    """Prompt user for input, showing and accepting a default value."""
    if default:
        user_input = input(f"{prompt} [{default}]: ").strip()
        return user_input if user_input else default
    else:
        return input(f"{prompt}: ").strip()


def load_json_config_file_from_appdata():
    """Load config from appdata, or run initial setup if not found."""

    if load_config_data_from_appdata():
        return  # Config already exists

    print("\n" + "=" * 50)
    print("Canvas Bot - Initial Configuration")
    print("=" * 50)
    print("\nThis appears to be your first time running Canvas Bot.")
    print("Let's set up your Canvas instance connection.\n")

    print("Enter your institution's Canvas identifier.")
    print("This is the subdomain in your Canvas URL.")
    print("  Example: For 'https://sfsu.instructure.com' enter: sfsu")
    print("  Example: For 'https://myschool.instructure.com' enter: myschool\n")

    canvas_domain = input("Canvas identifier: ").strip().lower()

    if not canvas_domain:
        print("[ERROR] Canvas identifier is required. Exiting.")
        sys.exit(1)

    # Auto-generate all URLs from the domain
    canvas_url = f"https://{canvas_domain}.instructure.com/courses/"
    api_path = f"https://{canvas_domain}.instructure.com/api/v1"
    studio_domain = f"{canvas_domain}.instructuremedia.com"

    app_config_dict = {
        'CANVAS_COURSE_PAGE_ROOT': canvas_url,
        'API_PATH': api_path,
        'CANVAS_DOMAIN': canvas_domain,
        'CANVAS_STUDIO_DOMAIN': studio_domain,
        'BOX_DOMAIN': '',
        'LIBRARY_PROXY_DOMAIN': '',
    }

    print(f"\n[Auto-configured]")
    print(f"  Canvas URL:     {canvas_url}")
    print(f"  API Path:       {api_path}")
    print(f"  Studio Domain:  {studio_domain}")

    print()
    confirm = input("Save this configuration? (yes/no): ").strip().lower()

    if confirm in ('yes', 'y', ''):
        save_config_data(app_config_dict)
        load_config_data_from_appdata()
        print("\n[OK] Configuration saved successfully!\n")
    else:
        print("\n[!] Configuration cancelled. Please run again to reconfigure.")
        sys.exit(0)


def configure_canvas_studio_api_key():
    """
    Refresh Canvas Studio tokens if they exist, or trigger setup if not.
    Sets tokens to environment variables.
    """
    studio_enabled = os.environ.get('studio_enabled', 'False')

    if studio_enabled != 'True':
        return  # Studio not enabled, nothing to do

    token, re_auth = get_canvas_studio_tokens()

    if token and re_auth:
        # Try to refresh existing tokens
        print("Refreshing Canvas Studio tokens...")
        new_token, new_re_auth = refresh_studio_token(re_auth)
        if new_token and new_re_auth:
            set_canvas_studio_api_key_to_environment_variable(new_token, new_re_auth)
            print("[OK] Canvas Studio tokens refreshed.\n")
        else:
            print("[!] Token refresh failed. You may need to re-authorize.")
    else:
        # No tokens found, need to authorize
        print("\nCanvas Studio is enabled but no tokens found.")
        print("Starting OAuth authorization...\n")
        token, re_auth = authorize_studio_token()
        if token and re_auth:
            set_canvas_studio_api_key_to_environment_variable(token, re_auth)
            print("[OK] Canvas Studio authorized successfully.\n")


def set_canvas_studio_config(force_config=False):
    """
    Configure Canvas Studio integration settings.
    Prompts user to enable/configure Canvas Studio if not already set.
    """
    # Check if already configured
    studio_enabled = os.environ.get('studio_enabled')

    if studio_enabled == 'True' and not force_config:
        # Already enabled, just refresh tokens
        configure_canvas_studio_api_key()
        return

    if studio_enabled == 'False' and not force_config:
        # Explicitly disabled, skip
        return

    # Not configured yet, or force_config is True - prompt user
    print("\n" + "-" * 50)
    print("Canvas Studio Integration (Optional)")
    print("-" * 50)
    print("\nCanvas Studio allows downloading and managing video")
    print("content hosted on your institution's Canvas Studio.")
    print("This requires OAuth client credentials from your admin.\n")

    while True:
        response = input("Enable Canvas Studio integration? (yes/no): ").strip().lower()

        if response in ('no', 'n'):
            save_config_data({'studio_enabled': False})
            print("[OK] Canvas Studio integration disabled.\n")
            return

        if response in ('yes', 'y'):
            break

        print("Please enter 'yes' or 'no'.")

    # User wants to enable Studio - collect credentials
    print("\n" + "-" * 50)
    print("Canvas Studio OAuth Setup")
    print("-" * 50)
    print("\nYou'll need OAuth credentials from your Canvas admin.")
    print("These are different from your personal API token.\n")

    client_id = input("Canvas Studio Client ID: ").strip()
    client_secret = input("Canvas Studio Client Secret: ").strip()

    if not client_id or not client_secret:
        print("[!] Client ID and Secret are required. Skipping Studio setup.")
        save_config_data({'studio_enabled': False})
        return

    # Save client credentials
    save_canvas_studio_client_keys(client_id, client_secret)
    print("[OK] Client credentials saved.\n")

    # Get Studio URLs - with helpful defaults based on Canvas domain
    canvas_domain = os.environ.get('CANVAS_DOMAIN', '')
    studio_domain = os.environ.get('CANVAS_STUDIO_DOMAIN', f'{canvas_domain}.instructuremedia.com')

    print("Enter Canvas Studio OAuth URLs:")
    print("(Press Enter to accept defaults shown in brackets)\n")

    default_auth_url = f"https://{studio_domain}/api/public/oauth/authorize"
    default_token_url = f"https://{studio_domain}/api/public/oauth/token"
    default_callback = "urn:ietf:wg:oauth:2.0:oob"

    auth_url = _prompt_with_default("  Authentication URL", default_auth_url)
    token_url = _prompt_with_default("  Token URL", default_token_url)
    callback_url = _prompt_with_default("  Callback URL", default_callback)

    # Save Studio config
    studio_config = {
        'studio_enabled': True,
        'CANVAS_STUDIO_AUTHENTICATION_URL': auth_url,
        'CANVAS_STUDIO_TOKEN_URL': token_url,
        'CANVAS_STUDIO_CALLBACK_URL': callback_url,
    }
    save_config_data(studio_config)
    load_config_data_from_appdata()

    print("\n[OK] Canvas Studio configuration saved.")
    print("Starting OAuth authorization...\n")

    # Now authorize
    token, re_auth = authorize_studio_token()
    if token and re_auth:
        set_canvas_studio_api_key_to_environment_variable(token, re_auth)
        print("[OK] Canvas Studio authorized successfully.\n")


def show_config_status():
    """Display current configuration status with masked sensitive values."""
    import json
    import keyring

    print("\n" + "=" * 60)
    print("Canvas Bot Configuration Status")
    print("=" * 60)

    # Get config file path
    appdata_path = os.environ.get("APPDATA", "")
    config_path = os.path.join(appdata_path, "canvas bot", "config.json")

    # Check if config file exists
    print(f"\nConfig file: {config_path}")
    if os.path.exists(config_path):
        print("Status: [EXISTS]")

        # Load and display config values
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)

            print("\n" + "-" * 60)
            print("Instance Settings")
            print("-" * 60)

            # Non-sensitive config values - show full value
            display_keys = [
                ('CANVAS_COURSE_PAGE_ROOT', 'Canvas URL'),
                ('API_PATH', 'API Path'),
                ('CANVAS_DOMAIN', 'Canvas Domain'),
                ('CANVAS_STUDIO_DOMAIN', 'Canvas Studio Domain'),
            ]

            for key, label in display_keys:
                value = config_data.get(key, '')
                if value:
                    print(f"  {label + ':':<25} {value}")
                else:
                    print(f"  {label + ':':<25} [not set]")

            print("\n" + "-" * 60)
            print("Canvas Studio OAuth URLs")
            print("-" * 60)

            studio_keys = [
                ('CANVAS_STUDIO_AUTHENTICATION_URL', 'Auth URL'),
                ('CANVAS_STUDIO_TOKEN_URL', 'Token URL'),
                ('CANVAS_STUDIO_CALLBACK_URL', 'Callback URL'),
            ]

            studio_enabled = config_data.get('studio_enabled', False)
            print(f"  {'Studio Enabled:':<25} {studio_enabled}")

            for key, label in studio_keys:
                value = config_data.get(key, '')
                if value:
                    print(f"  {label + ':':<25} {value}")
                else:
                    print(f"  {label + ':':<25} [not set]")

        except (json.JSONDecodeError, IOError) as e:
            print(f"  [ERROR] Could not read config file: {e}")
    else:
        print("Status: [NOT FOUND] - Run canvas_bot to configure")

    # Check credentials in Windows Credential Vault
    print("\n" + "-" * 60)
    print("Credentials (Windows Credential Vault)")
    print("-" * 60)

    def mask_value(value, show_chars=4):
        """Mask a sensitive value, showing only first few chars."""
        if not value:
            return "[not set]"
        if len(value) <= show_chars:
            return "*" * len(value)
        return value[:show_chars] + "*" * (len(value) - show_chars)

    # Canvas API Token
    try:
        api_token = keyring.get_password("ACCESS_TOKEN", "canvas_bot")
        print(f"  {'Canvas API Token:':<25} {mask_value(api_token)}")
    except Exception:
        print(f"  {'Canvas API Token:':<25} [error reading]")

    # Canvas Studio Client ID
    try:
        studio_client_id = keyring.get_password("STUDIO_CLIENT_ID", "canvas_bot")
        print(f"  {'Studio Client ID:':<25} {mask_value(studio_client_id)}")
    except Exception:
        print(f"  {'Studio Client ID:':<25} [error reading]")

    # Canvas Studio Client Secret
    try:
        studio_client_secret = keyring.get_password("STUDIO_CLIENT_SECRET", "canvas_bot")
        print(f"  {'Studio Client Secret:':<25} {mask_value(studio_client_secret, 2)}")
    except Exception:
        print(f"  {'Studio Client Secret:':<25} [error reading]")

    # Canvas Studio Access Token
    try:
        studio_token = keyring.get_password("CANVAS_STUDIO_TOKEN", "canvas_bot")
        print(f"  {'Studio Access Token:':<25} {mask_value(studio_token)}")
    except Exception:
        print(f"  {'Studio Access Token:':<25} [error reading]")

    # Canvas Studio Refresh Token
    try:
        studio_refresh = keyring.get_password("CANVAS_STUDIO_RE_AUTH_TOKEN", "canvas_bot")
        print(f"  {'Studio Refresh Token:':<25} {mask_value(studio_refresh)}")
    except Exception:
        print(f"  {'Studio Refresh Token:':<25} [error reading]")

    print("\n" + "=" * 60)
    print("Use --reset_canvas_params to reconfigure Canvas settings")
    print("Use --reset_canvas_studio_params to reconfigure Studio settings")
    print("=" * 60 + "\n")


def list_patterns(category=None):
    """List all categories or patterns in a specific category."""
    patterns = read_re(substitute=False)

    if category is None:
        print("Pattern Categories:")
        print("-" * 40)
        for key in patterns.keys():
            count = len(patterns[key]) if isinstance(patterns[key], list) else 1
            print(f"  {key} ({count} patterns)")
    else:
        if category not in patterns:
            print(f"Error: Category '{category}' not found")
            sys.exit(1)
        print(f"Patterns in '{category}':")
        print("-" * 40)
        items = patterns[category]
        if isinstance(items, list):
            for i, p in enumerate(items, 1):
                print(f"  {i}. {p}")
        else:
            print(f"  {items}")


def add_pattern(category, pattern, skip_confirm=False):
    """Add a pattern to a category."""
    try:
        re.compile(pattern)
    except re.error as e:
        print(f"Error: Invalid regex - {e}")
        sys.exit(1)

    patterns = read_re(substitute=False)
    if category not in patterns:
        print(f"Error: Category '{category}' not found")
        sys.exit(1)

    if isinstance(patterns[category], list):
        if pattern in patterns[category]:
            print(f"Pattern already exists in '{category}'")
            sys.exit(0)

    print(f"\nCategory: {category}")
    print("-" * 40)
    print(f"+ {pattern}")
    print()

    if not skip_confirm:
        confirm = input("Add this pattern? [y/N]: ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            sys.exit(0)

    if isinstance(patterns[category], list):
        patterns[category].append(pattern)
    else:
        patterns[category] = pattern

    write_re(patterns)
    print("Pattern added.")


def remove_pattern(category, pattern, skip_confirm=False):
    """Remove a pattern from a category."""
    patterns = read_re(substitute=False)
    if category not in patterns:
        print(f"Error: Category '{category}' not found")
        sys.exit(1)

    if isinstance(patterns[category], list):
        if pattern not in patterns[category]:
            print(f"Pattern not found in '{category}'")
            sys.exit(1)
    else:
        if patterns[category] != pattern:
            print(f"Pattern not found in '{category}'")
            sys.exit(1)

    print(f"\nCategory: {category}")
    print("-" * 40)
    print(f"- {pattern}")
    print()

    if not skip_confirm:
        confirm = input("Remove this pattern? [y/N]: ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            sys.exit(0)

    if isinstance(patterns[category], list):
        patterns[category].remove(pattern)
    else:
        patterns[category] = ""

    write_re(patterns)
    print("Pattern removed.")


def test_pattern(test_string):
    """Test which categories match a string."""
    from sorters.sorters import (
        document_content_regex, image_content_regex,
        web_video_content_regex, video_file_content_regex,
        web_audio_content_regex, audio_file_content_regex,
        web_document_applications_regex, file_storage_regex,
        canvas_studio_embed, ignore_list_regex
    )

    matchers = [
        ("document_content_regex", document_content_regex),
        ("image_content_regex", image_content_regex),
        ("web_video_resources_regex", web_video_content_regex),
        ("video_file_resources_regex", video_file_content_regex),
        ("web_audio_resources_regex", web_audio_content_regex),
        ("audio_file_resources_regex", audio_file_content_regex),
        ("web_document_applications_regex", web_document_applications_regex),
        ("file_storage_regex", file_storage_regex),
        ("canvas_studio_embed", canvas_studio_embed),
        ("ignore_list_regex", ignore_list_regex),
    ]

    print(f"Testing: {test_string}")
    print("-" * 40)
    matched = False
    for name, regex in matchers:
        if regex.match(test_string):
            print(f"  MATCH: {name}")
            matched = True

    if not matched:
        print("  No matches (would be classified as Unsorted)")


def validate_pattern(pattern):
    """Validate regex syntax."""
    try:
        compiled = re.compile(pattern, re.IGNORECASE)
        print(f"Valid regex: {pattern}")
        print(f"  Flags: IGNORECASE")
        print(f"  Groups: {compiled.groups}")
    except re.error as e:
        print(f"Invalid regex: {e}")
        sys.exit(1)


def reset_patterns(skip_confirm=False):
    """Reset patterns to bundled defaults."""
    print("\nThis will reset all patterns to the original defaults.")
    print("Any custom patterns you added will be lost.")
    print()

    if not skip_confirm:
        confirm = input("Reset patterns to defaults? [y/N]: ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            sys.exit(0)

    if reset_re():
        print("Patterns reset to defaults.")
    else:
        print("No custom patterns file found (already using defaults).")


class CanvasBot(CanvasCourseRoot):
    """
    Wraps Canvas Course Root Class
    """
    def __init__(self, course_id=None):
        if course_id:
            self.detect_and_set_config()
            super().__init__(str(course_id))

    def detect_and_set_config(self):
        """Load existing configuration or run initial setup."""
        print("\nLoading configuration...")
        load_json_config_file_from_appdata()
        check_if_api_key_exists()
        set_canvas_studio_config()
        print("Configuration loaded.\n")


    def reset_config(self):
        """Clear all configuration and re-run setup."""
        print("\n" + "=" * 50)
        print("Resetting Canvas Bot Configuration")
        print("=" * 50)
        print("\nClearing saved credentials and settings...")
        delete_canvas_api_key()
        delete_config_file_from_appdata()
        print("[OK] Configuration cleared.\n")
        self.detect_and_set_config()

    def reset_canvas_studio_config(self):
        """Clear Canvas Studio configuration and re-run setup."""
        print("\n" + "=" * 50)
        print("Resetting Canvas Studio Configuration")
        print("=" * 50)
        print("\nClearing Canvas Studio credentials...")
        delete_canvas_studio_client_keys()
        delete_canvas_studio_tokens()
        print("[OK] Studio credentials cleared.\n")
        set_canvas_studio_config(force_config=True)


    def start(self):
        print(f"Starting Canvas Bot - {version} ")
        self.initialize_course()

    def print_content_tree(self):
        if self.exists:
            return self.canvas_tree.show_content_only()

    def print_full_course(self):
        if self.exists:
            return self.canvas_tree.show_nodes()


if __name__=='__main__':

    @click.command()
    @click.help_option('-h', '--help', help='Canvas Bot - A tool for downloading and auditing Canvas LMS course content. '
                                            'Discovers all content in a course (modules, pages, assignments, quizzes, files), '
                                            'categorizes embedded links (documents, videos, audio, images), and exports to '
                                            'organized folders or Excel/JSON for accessibility auditing. '
                                            'Requires a Canvas API access token (Account > Settings > New Access Token).')

    # === Course Selection ===
    @click.option('--course_id', type=click.STRING,
                  help='Canvas course ID to process. Find it in the course URL: canvas.edu/courses/[COURSE_ID]')
    @click.option('--course_id_list', type=click.STRING,
                  help='Path to text file with multiple course IDs (one per line) for batch processing.')

    # === Output Options ===
    @click.option('--download_folder', type=click.STRING,
                  help='Directory to download files to. By default downloads documents only (PDF, DOCX, PPTX, etc). '
                       'Files are organized into subfolders matching the course module structure.')
    @click.option('--output_as_json', type=click.STRING,
                  help='Directory to save JSON export. Creates a structured inventory of all course content '
                       'with metadata (URLs, titles, source pages, content types).')
    @click.option('--output_as_excel', type=click.STRING,
                  help='Directory to save Excel workbook (.xlsm). Creates multi-sheet report for accessibility '
                       'auditing with separate tabs for Documents, Videos, Audio, Images, and tracking columns.')

    # === Content Inclusion Flags ===
    @click.option('--include_video_files', is_flag=True,
                  help='Also download video files (MP4, MOV, MKV, AVI, WebM). These can be large.')
    @click.option('--include_audio_files', is_flag=True,
                  help='Also download audio files (MP3, M4A, WAV, OGG).')
    @click.option('--include_image_files', is_flag=True,
                  help='Also download image files (JPG, PNG, GIF, SVG, WebP).')
    @click.option('--download_hidden_files', is_flag=True,
                  help='Include content that is hidden/unpublished in Canvas (not visible to students).')

    # === Download Behavior ===
    @click.option('--flatten', is_flag=True,
                  help='Download all files to a single flat directory instead of preserving module folder structure.')
    @click.option('--flush_after_download', is_flag=True,
                  help='Delete downloaded files after processing. Use for temporary extraction workflows.')

    # === Display & Debug ===
    @click.option('--print_content_tree', is_flag=True,
                  help='Print course tree showing only resources that contain content.')
    @click.option('--print_full_course', is_flag=True,
                  help='Print complete course tree including all resources.')

    # === Configuration ===
    @click.option('--config_status', is_flag=True,
                  help='Display current configuration status. Shows all settings with sensitive values masked.')
    @click.option('--reset_canvas_params', is_flag=True,
                  help='Clear and reconfigure Canvas API token and instance URL (stored in Windows Credential Vault).')
    @click.option('--reset_canvas_studio_params', is_flag=True,
                  help='Clear and reconfigure Canvas Studio OAuth credentials (client ID, secret, tokens).')

    # === Video Captioning ===
    @click.option('--caption_file_location', type=click.STRING,
                  help='Path to caption file (.vtt, .srt) to upload to Canvas Studio. '
                       'Requires --canvas_studio_media_id.')
    @click.option('--canvas_studio_media_id', type=click.STRING,
                  help='Canvas Studio media ID for caption upload target. '
                       'Requires --caption_file_location.')

    # === Pattern Management ===
    @click.option('--patterns-list', 'patterns_list', default=None, is_flag=False, flag_value='',
                  help='List pattern categories. Optionally specify CATEGORY to see patterns in it.')
    @click.option('--patterns-add', 'patterns_add', nargs=2, type=str, default=None,
                  help='Add PATTERN to CATEGORY. Usage: --patterns-add CATEGORY PATTERN')
    @click.option('--patterns-remove', 'patterns_remove', nargs=2, type=str, default=None,
                  help='Remove PATTERN from CATEGORY. Usage: --patterns-remove CATEGORY PATTERN')
    @click.option('--patterns-test', 'patterns_test', default=None,
                  help='Test which categories match STRING.')
    @click.option('--patterns-validate', 'patterns_validate', default=None,
                  help='Validate PATTERN regex syntax without saving.')
    @click.option('--patterns-reset', 'patterns_reset', is_flag=True,
                  help='Reset patterns to bundled defaults (removes customizations).')
    @click.option('-y', '--yes', 'skip_confirm', is_flag=True,
                  help='Skip confirmation for pattern changes.')

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
             print_content_tree,
             print_full_course,
             config_status,
             reset_canvas_params,
             reset_canvas_studio_params,
             caption_file_location,
             canvas_studio_media_id,
             patterns_list,
             patterns_add,
             patterns_remove,
             patterns_test,
             patterns_validate,
             patterns_reset,
             skip_confirm
             ):

        # Handle --config_status first (doesn't require course_id)
        if config_status:
            show_config_status()
            sys.exit(0)

        # Handle --reset_canvas_studio_params (doesn't require course_id)
        if reset_canvas_studio_params:
            # Load existing config first so we have the domain info
            load_config_data_from_appdata()
            delete_canvas_studio_client_keys()
            delete_canvas_studio_tokens()
            print("\n[OK] Canvas Studio credentials cleared.")
            set_canvas_studio_config(force_config=True)
            print("[OK] Canvas Studio reconfigured.")
            sys.exit(0)

        # Handle pattern management options (don't require course_id)
        if patterns_list is not None:
            list_patterns(patterns_list if patterns_list != '' else None)
            sys.exit(0)

        if patterns_add:
            add_pattern(patterns_add[0], patterns_add[1], skip_confirm)
            sys.exit(0)

        if patterns_remove:
            remove_pattern(patterns_remove[0], patterns_remove[1], skip_confirm)
            sys.exit(0)

        if patterns_test:
            test_pattern(patterns_test)
            sys.exit(0)

        if patterns_validate:
            validate_pattern(patterns_validate)
            sys.exit(0)

        if patterns_reset:
            reset_patterns(skip_confirm)
            sys.exit(0)

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
            "print_content_tree": print_content_tree,
            "print_full_course": print_full_course,
            "reset_params": reset_canvas_params,
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
                    caption_status = add_caption_to_canvas_studio_video(course_id,
                                                       params['caption_file_location'],
                                                       params['canvas_studio_media_id'])
                    if caption_status is False:
                        return sys.exit(3) # failure
                    sys.exit()

                else:
                    click.echo("Must include both caption file location and canvas studio media id")
                    sys.exit(1)

            if reset_canvas_params:
                bot.reset_config()


            if course_id:
                bot.start()
            else:
                print("No course ID provided. Exiting")
                sys.exit()

            if print_content_tree:
                bot.print_content_tree()

            if print_full_course:
                bot.print_full_course()

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


    if len(sys.argv) == 1:
        from gui.app import CanvasBotGUI
        CanvasBotGUI().run()
    else:
        try:
            main()
        except Exception as exc:
            log.exception(exc)
            raise exc


