import posixpath as path

from urllib.parse import parse_qs, urlparse, urlunparse


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

