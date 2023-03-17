import posixpath as path
import re

from urllib.parse import parse_qs, urlparse, urlunparse


def is_url(string):
    url_pattern = re.compile(
        r'^(?:http|ftp)s?://'  # Scheme (http, https, ftp)
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # Domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP address
        r'(?::\d+)?'  # Optional port number
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

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

