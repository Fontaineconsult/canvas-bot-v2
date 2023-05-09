import posixpath as path
import re, os

from urllib.parse import parse_qs, urlparse, urlunparse

from sorters.sorters import file_name_extractor


def shorten_filename_while_keeping_extension(filename: str, max_length: int) -> str:
    """
    Shortens a filename while keeping the file extension.
    :param filename: The filename to shorten.
    :param max_length: The maximum length of the filename.
    :return: The shortened filename.
    """
    if len(filename) <= max_length:
        return filename

    name, extension = path.splitext(filename)
    return name[:max_length - len(extension)] + extension


def sanitize_windows_filename(filename: str, folder=False) -> str:
    # Remove invalid characters

    filename = filename.encode('ascii', errors='ignore').decode('ascii')


    invalid_chars = r'[,%<>:"/\\|?*\x00-\x1f]'

    if folder:
        invalid_chars = r'[,\.%<>:"/\\|?*\x00-\x1f]'

    sanitized_filename = re.sub(invalid_chars, "", filename)

    # Add a hyphen to the end of reserved names
    reserved_names = [
        "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5",
        "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4",
        "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    ]
    name_without_extension = sanitized_filename.split('.')[0]

    if name_without_extension.upper() in reserved_names:
        name_parts = sanitized_filename.split('.')
        name_parts[0] += '-'
        sanitized_filename = '.'.join(name_parts)
    return sanitized_filename




def is_url(string: str) -> bool:

    string = string.replace(' ', '')

    url_pattern = re.compile(
        r'^(?:http|ftp)s?://'  # Scheme (http, https, ftp)
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # Domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP address
        r'(?::\d+)?'  # Optional port number
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    if string.startswith('www.'):
        return True

    return bool(url_pattern.match(string))


def clean_url(url, **kwargs):
    return remove_preceding_forward_slashes(url)


def extract_url_query_param(url):

    target = parse_qs(urlparse(url).query)['url'][0]
    p = urlparse(target)
    q = p._replace(path=path.join(path.dirname(path.dirname(p.path)), path.basename(p.path)))
    return urlunparse(q)


def remove_query_params(url):
    parsed_url = urlparse(url)
    cleaned_url = parsed_url._replace(query="")
    return urlunparse(cleaned_url)


def remove_preceding_forward_slashes(url):
    if url[0:2] == "//":
        return url[2:]
    else:
        return url


def remove_trailing_path_segments(url):
    """
     remove trailing path segments from a url if the url contains a file name
    :param url:
    :return:
    """
    from urllib.parse import urlparse, urlunparse
    parsed_url = urlparse(remove_query_params(url))

    for count, component in enumerate(parsed_url.path.split('/')):
        if not file_name_extractor.match(component):
            continue
        if file_name_extractor.match(component):
            fixed_paths = [item for item in parsed_url.path.split('/')[:count + 1] if item != '']
            return urlunparse(parsed_url._replace(path=path.join(*fixed_paths)))

    return
