from bs4 import BeautifulSoup

from sorters.sorters import resource_node_regex


def get_href_links_from_html_a_tag(html_body):

    if html_body is None:
        return list()
    soup = BeautifulSoup(html_body, "html.parser")
    if soup:
        return [(a_tag.get('href'), a_tag.text.strip()) for a_tag in soup.find_all('a')
                if a_tag.get('href') is not None and resource_node_regex.search(a_tag.get('href')) is None]


def get_src_links_from_html_iframe_tag(html_body):

    if html_body is None:
        return list()
    soup = BeautifulSoup(html_body, "html.parser")
    print("IFRAME", soup)
    if soup:
        return [(a_tag.get('src'), a_tag.text.strip()) for a_tag in soup.find_all('iframe')
                if a_tag.get('src') is not None and resource_node_regex.search(a_tag.get('src')) is None]


def get_src_links_from_img_tag(html_body):

    if html_body is None:
        return list()
    soup = BeautifulSoup(html_body, "html.parser")
    if soup:
        return [(a_tag.get('src'), a_tag.text.strip()) for a_tag in soup.find_all('img')
                if a_tag.get('src') is not None and resource_node_regex.search(a_tag.get('src')) is None]


def get_src_links_from_video_tag(html_body):

    if html_body is None:
        return list()
    soup = BeautifulSoup(html_body, "html.parser")
    if soup:
        return [(a_tag.get('src'), a_tag.text.strip()) for a_tag in soup.find_all('video')
                if a_tag.get('src') is not None and resource_node_regex.search(a_tag.get('src')) is None]


def get_data_api_links_from_html(html_body):
    soup = BeautifulSoup(html_body, "html.parser")
    if soup:
        return [(a_tag.get('data-api-endpoint'), a_tag.text.strip())
                for a_tag in soup.find_all('a') if a_tag.get('data-api-endpoint') is not None]