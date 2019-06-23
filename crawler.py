from sys import argv, exit
from validators import url
from collections import defaultdict
from multiprocessing import Pool
from itertools import chain
import requests
from lxml import html
from pprint import pprint
from multiprocessing.context import TimeoutError as MPTimeoutError
import networkx as nx
from matplotlib import pyplot as plt

default_origin = 'https://www.wikipedia.org/'
default_output_file_name = 'graph.out'
default_statistics_file_name = 'stats.out'
default_max_n_links = 100
default_timeout = 60
default_max_n_threads = 4

origin_url = default_origin
output_file_name = default_output_file_name
statistics_file_name = default_statistics_file_name
max_n_links = default_max_n_links
timeout = default_timeout
max_n_threads = default_max_n_threads
try:
    origin_url = argv[1]
    output_file_name = argv[2]
    statistics_file_name = argv[3]
    max_n_links = int(argv[4])
    timeout = int(argv[5])
    max_n_threads = int(argv[6])
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
            except requests.exceptions.ConnectionError:
                print('Connection issue with some URLs')

        hyperlink_pairs = zip(boundary, discovered_urls)
        for _ in range(boundary_limit):
            try:
                url, linked_urls = next(hyperlink_pairs)
            except StopIteration:
                break
            hyperlinks_to[url] = linked_urls
            hyperlinked_from.update({link: url for link in linked_urls})
            print(f'Discovered {len(linked_urls)} link(s) from {url}')

        boundary = [link for link in chain(*discovered_urls) if link not in hyperlinks_to and link not in boundary]

        print(f'Added {len(boundary)} link(s) to boundary')

    print(f'Crawling complete, {sum([len(v) for _, v in hyperlinks_to.items()])} results stored in {output_file_name}')

    link_separator = '\n\t'
    output_lines = [f'{url} linked to:'
                    f'{link_separator}{link_separator.join(linked_to)}' for url, linked_to in hyperlinks_to.items()]
    with open(output_file_name, mode='wb+') as f:
        for line in output_lines:
            f.write((line + '\n\n').encode('utf-8'))

    print('Generating statistics')

    graph = nx.DiGraph(hyperlinks_to)

    # Diameter
    try:
        diameter = nx.diameter(graph)
    except nx.NetworkXError:
        diameter = 'infinite'

    def gen_len_nested(generator):
        return sum(1 for e in generator for _ in e)

    # Average distance
    lengths = nx.all_pairs_shortest_path_length(graph)
    n_lengths = gen_len_nested(lengths)
    if n_lengths == 0:
        print('Unable to generate statistics since there are zero paths')
        exit()
    lengths = nx.all_pairs_shortest_path_length(graph)
    average_distance = sum(d for d in lengths if isinstance(d, int)) / n_lengths

    def gen_len(generator):
        return sum(1 for _ in generator)

    # Number of SCCs
    n_sscs = gen_len(nx.strongly_connected_components(graph))

    # TODO: Visualization of graph

    incoming = {url: len(hyperlinks_to[url]) for url in hyperlinks_to}
    outgoing = {url: len(hyperlinked_from[url]) for url in hyperlinked_from}

    incoming_stats = link_separator + link_separator.join([f'{url}: {n}' for url, n in incoming.items()])
    outgoing_stats = link_separator + link_separator.join([f'{url}: {n}' for url, n in outgoing.items()])

    # Report
    with open(statistics_file_name, mode='w+') as f:
        f.write(f'Graph Statistics\n'
                f'diameter: {diameter}\n'
                f'average shortest distance between two points: {average_distance}\n'
                f'number of strongly connected components: {n_sscs}\n'
                f'distribution of incoming links:\n'
                f'{incoming_stats}\n'
                f'distribution of outgoing links:n\n'
                f'{outgoing_stats}\n')

    print(f'Statistics written to {statistics_file_name}')
