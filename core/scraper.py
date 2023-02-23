from bs4 import BeautifulSoup

from sorters.sorters import resource_node_regex


def get_general_links_from_html(html_body):
    soup = BeautifulSoup(html_body)
    if soup:
        return [(a_tag.get('href'), a_tag.text.strip()) for a_tag in soup.find_all('a') if not resource_node_regex.search(a_tag.get('href'))]


def get_data_api_links_from_html(html_body):
    soup = BeautifulSoup(html_body)
    if soup:
        return [(a_tag.get('data-api-endpoint'), a_tag.text.strip()) for a_tag in soup.find_all('a') if a_tag.get('data-api-endpoint') is not None]