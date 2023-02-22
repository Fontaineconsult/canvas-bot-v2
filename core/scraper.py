from bs4 import BeautifulSoup


def get_general_links_from_html(html_body):
    soup = BeautifulSoup(html_body)
    if soup:
        return [(a_tag.get('href'), a_tag.text.strip()) for a_tag in soup.find_all('a')]


def get_data_api_links_from_html(html_body):
    soup = BeautifulSoup(html_body)
    if soup:
        return [(a_tag.get('data-api-endpoint'), a_tag.text.strip()) for a_tag in soup.find_all('a') if a_tag.get('data-api-endpoint') is not None]