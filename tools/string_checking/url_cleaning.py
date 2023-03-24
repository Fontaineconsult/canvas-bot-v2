import posixpath as path
import re, os

from urllib.parse import parse_qs, urlparse, urlunparse


def sanitize_windows_filename(filename: str) -> str:
    # Remove invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
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
    url = extract_url_query_param(url)
    return remove_preceding_forward_slashes(url)


def extract_url_query_param(url):
    try:
        target = parse_qs(urlparse(url).query)['url'][0]
        p = urlparse(target)
        q = p._replace(path=path.join(path.dirname(path.dirname(p.path)), path.basename(p.path)))
        return urlunparse(q)
    except KeyError:
        return url


def remove_preceding_forward_slashes(url):
    if url[0:2] == "//":
        return url[2:]
    else:
        return url

