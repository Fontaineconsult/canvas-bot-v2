import posixpath as path

from urllib.parse import parse_qs, urlparse, urlunparse


def clean_url(url, **kwargs):

    return remove_preceding_forward_slashes(url)


def extract_from_outlook_safelink(url):

    target = parse_qs(urlparse(url).query)['url'][0]
    p = urlparse(target)
    q = p._replace(path=path.join(path.dirname(path.dirname(p.path)), path.basename(p.path)))
    return urlunparse(q)

def remove_preceding_forward_slashes(url):
    if url[0:2] == "//":
        return url[2:]
    else:
        return url

