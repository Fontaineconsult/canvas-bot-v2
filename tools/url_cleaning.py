import posixpath as path
from urllib import *
from urllib.parse import parse_qs, urlparse, urlunparse


def extract_from_outlook_safelink(url):

    target = parse_qs(urlparse(url).query)['url'][0]
    p = urlparse(target)
    q = p._replace(path=path.join(path.dirname(path.dirname(p.path)), path.basename(p.path)))
    return urlunparse(q)



