from sys import argv, exit
from validators import url
from collections import defaultdict
from multiprocessing import Pool
from itertools import chain
import scrapy
import requests
from lxml import html
from pprint import pprint
from multiprocessing.context import TimeoutError as MPTimeoutError

default_origin = 'https://www.wikipedia.org/'
default_output_file_name = 'out.txt'
default_max_n_links = 100
default_timeout = 60
default_max_n_threads = 10
# default_crawl_relative_paths = True

'''
Usage:
python ./crawler.py [origin_url [output_file_name [max_n_links [timeout [max_n_threads]]]]]
'''

origin_url = default_origin
output_file_name = default_output_file_name
max_n_links = default_max_n_links
timeout = default_timeout
max_n_threads = default_max_n_threads
# crawl_relative_paths = default_crawl_relative_paths
try:
    origin_url = argv[1]
    output_file_name = argv[2]
    max_n_links = int(argv[3])
    timeout = int(argv[4])
    max_n_threads = int(argv[5])
    # crawl_relative_paths = bool(argv[6])
except IndexError:
    pass


def urls_on_page(url):
    try:
        url_html = html.fromstring(requests.get(url).content)
        url_html.make_links_absolute(url)
        return [linked_url for linked_url in url_html.xpath('//a/@href')]
    except TimeoutError:
        print(f'{url} timed out')
        return []


if __name__ == "__main__":

    n_max_iterations = max_n_links
    n_iterations = 0

    if not url(origin_url):
        print(f'Bad origin url: {origin_url}')
        exit()

    print(f'Starting web crawl at {origin_url}')

    boundary = defaultdict(list)
    boundary[origin_url] = list()
    hyperlinks_to = defaultdict(list)
    hyperlinked_from = defaultdict(list)

    while len(hyperlinks_to) < max_n_links and len(boundary) > 0 and n_iterations < n_max_iterations:

        n_iterations += 1
        print(f'Beginning degree-{n_iterations} search from {origin_url}')

        boundary_limit = min(max_n_links - len(hyperlinks_to), len(boundary))
        actual_n_threads = min(max_n_threads, boundary_limit)

        print(f'Spawning {actual_n_threads} thread(s) to explore boundary of {boundary_limit} element(s)')
        with Pool(processes=actual_n_threads) as scraping_pool:

            scraping_results = scraping_pool.map_async(urls_on_page, boundary)
            try:
                discovered_urls = scraping_results.get(timeout=timeout)
            except MPTimeoutError:
                print('Ran out of time: '
                      'not enough processing power, consider adding more threads or increasing timeout')
                break

        hyperlink_pairs = zip(boundary, discovered_urls)
        for _ in range(boundary_limit):
            url, linked_urls = next(hyperlink_pairs)
            hyperlinks_to[url] = linked_urls
            hyperlinked_from.update({link: url for link in linked_urls})
            print(f'Discovered {len(linked_urls)} link(s) from {url}')

        boundary = [link for link in chain(*discovered_urls) if link not in hyperlinks_to and link not in boundary]

        print(f'Added {len(boundary)} link(s) to boundary')

    print(f'Crawling complete, {sum([len(v) for _, v in hyperlinks_to.items()])} results stored in {output_file_name}')

    link_separator = '\n\t'
    output_lines = [f'{url} linked to: {link_separator.join(linked_to)}' for url, linked_to in hyperlinks_to.items()]
    with open(output_file_name, mode='wb+') as f:
        for line in output_lines:
            f.write((line + '\n\n').encode('utf-8'))
