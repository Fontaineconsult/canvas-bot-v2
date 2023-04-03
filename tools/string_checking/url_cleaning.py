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

    invalid_chars = r'[%<>:"/\\|?*\x00-\x1f]'

    if folder:
        invalid_chars = r'[\.%<>:"/\\|?*\x00-\x1f]'

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
    print(p)
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


print(remove_trailing_path_segments("https://rightslink-prd-copyright-com.s3.amazonaws.com/getitnow/fulfillment/6403289.pdf?X-Amz-Security-Token=IQoJb3JpZ2luX2VjEE4aCXVzLWVhc3QtMSJHMEUCIQD%2BJKf7xmR6WGcLuF1Ee3klr37w7guHC46kkVrUz%2BfQSQIgZkjOSsoaTIOK0zJnbGqpeRO1ebs0SedSogzZMsviGdEqtAMINhACGgwyNzI5MzQ1Njk5NTIiDLm8EX%2FzPKG7k50pXSqRA%2BF48nTMtJlHcC3bC3fZiV8ZdYRak%2BSogL2xhvRVoGgrnFk2NdAUWV7kLj0OA9A9lhUN2OwyruSk5EI9cfsYvFbLd2Bp%2BR1yUWgXHohhJPlQTu32b02FX3Qq86IISs1znjYUHko3dC1udxQcQG109GOG3csr%2F3z17vKxBvRCTow0IMFddRjCvMSb38KSItiQSAd4wWsvqQ2MbUPxIlKpDJjJcSew3Pz%2BvDMASWq0oAHsdKqAmulymSJB0COBOZ2YtZ0NTYHlap%2BKgpMBrHWAc2e1zfhNWAuahthLbt0qKEpepDz8Hyrig3yFtKDFZOMA0L0ef%2FQFsPhxqVZ%2BZhR1ROnU9w4%2F5J73W9ZM8zc%2B3Ar8LFnDqJxSmYvFN55HvT%2FImA32BEZ0hDP5Dq6BpDhuJJlbqMzbDEOyluBouu0ZDnaFPMjhvI83z5tX0vDD0xmOX3KUNUSK5Ee%2FfM267OuEZriIOx1Nqq6i%2BeLahB54h6mWlpllvwBTAU9zAWchH9KW6ro67FihGAB8FaGXr8FNx8P%2FMJes9vkFOusBO25HzRF9qbgO8Xz3J%2F6Wt84mJi1L%2FUKOCtFFOU%2FOKA5Q%2BWc0ct8%2FCYOky65%2FF152mgXXCgz7kgo%2FZKQLuMo25X3rfn0ULEMF7xnzdsLSlGI%2FQO8PY62HWFRWINOKtci9msiUge5RA00%2FnjdW82di2PAL%2FzmVrH4HbG7u025CzcPdDTx1re0YSxcVg%2B8mioFEuM42CNtA5fB0LLZqhhVoHi0lyOIYMWy%2FmoczXR0B1BgU%2FRI3vypJfSBq0pHfe6ZnwyB4Jf866Q08pbFJUgGsErMhkJhgC2e6rSOdt7nwJpvkBiU6sSnAnnw5YQ%3D%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20200819T220224Z&X-Amz-SignedHeaders=host&X-Amz-Expires=86400&X-Amz-Credential=ASIAT7DBLA7QCPHZLCHE%2F20200819%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=2066081be7a1ecb589ecfca5e5f6ac6e7d73a338474fddbd5a0b30313c468597"))