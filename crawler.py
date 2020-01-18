from urllib import request, parse
from http import client
from html import parser
import queue
import threading
import time
import contextlib

import utils


# Defaults
DEFAULT_START_URL = r'https://www.wikipedia.org/'
DEFAULT_THREAD_LIMIT = 4
DEFAULT_PATH = 'web.save'


class PageParserError(ValueError):
    """Raised when an HTML page cannot be parsed"""
    

class URLExtractor(parser.HTMLParser):
    
    def __init__(self, url, data):
        super().__init__()
        self._url = url
        self._data = data
        self._found_links = set()
        
    def links(self):
        self.feed(self._data)
        return self._found_links
    
    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return
        for name, val in attrs:
            if name == 'href':
                self._found_links.add(parse.urljoin(self._url, val))
                return

    def error(self, message):
        raise PageParserError(message)


class URLRetrievalFailure(ConnectionError):
    """Raised when a URL cannot be visited"""


def urls_on_page(url):
    with request.urlopen(url) as response:
        # Some URLs may return other, valid responses, but they are not currently supported
        if not isinstance(response, client.HTTPResponse):
            raise URLRetrievalFailure()
        body = response.read()
    url_extractor = URLExtractor(url=url, data=body.decode())
    return url_extractor.links()


def crawl(url, url_graph, url_graph_lock):
    """Crawls the given URL and updates the url_graph, uses the url_graph_lock for synchronized access
    :returns All newly found URLs which are not already in the url_graph
    """
    
    linked_urls = urls_on_page(url)

    with url_graph_lock:
        url_graph[url] = linked_urls
        return [linked_url for linked_url in linked_urls if linked_url not in url_graph]


_print_lock = threading.Lock()


def sync_print(msg, *args, **kwargs):
    with _print_lock:
        print(msg, *args, **kwargs)
        
        
class StatefulThread(threading.Thread):
    
    def __init__(self, target, start_immediately=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = start_immediately


def crawl_worker_task(running_event, url_boundary_queue, url_graph, url_graph_lock):
    while running_event.is_set():
        url = url_boundary_queue.get()
        sync_print(f'Crawling {url}')
        try:
            linked_urls = crawl(url, url_graph, url_graph_lock)
            sync_print(f'Finished crawling {url}')
            url_boundary_queue.task_done()
            for linked_url in linked_urls:
                url_boundary_queue.put(linked_url)
        except Exception as e:
            sync_print(f'Failed to crawl {url}, encountered {e}')

    
def main(start_url, thread_limit, path):
    url_boundary_queue = queue.Queue()
    url_boundary_queue.put(start_url)
    url_graph = dict()
    urls_graph_lock = threading.Lock()
    
    if path:
        with contextlib.suppress(FileNotFoundError, EOFError):
            url_boundary_queue, url_graph = utils.load(path)
            sync_print(f'Loaded from {path}')
            
    running_event = threading.Event()
    
    threads = [threading.Thread(target=crawl_worker_task,
                                args=(running_event, url_boundary_queue, url_graph, urls_graph_lock),
                                daemon=True) for _ in range(int(thread_limit))]
    
    running_event.set()
    for thread in threads:
        thread.start()
        
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        sync_print('Waiting for threads to finish executing')
        running_event.clear()
        while any([thread.is_alive() for thread in threads]):
            continue
    
    if path:
        utils.save(url_boundary_queue, url_graph, path)
        sync_print(f'Saved to {path}')

    # TODO:
    #   - Visualization


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Crawls the web')
    parser.add_argument('-s', '--start-url', default=DEFAULT_START_URL,
                        help=f'the starting point of the crawl, defaults to {DEFAULT_START_URL}')
    parser.add_argument('-t', '--thread-limit', default=DEFAULT_THREAD_LIMIT,
                        help=f'the number of threads to use when crawling, defaults to {DEFAULT_THREAD_LIMIT}')
    parser.add_argument('-p', '--path', default=DEFAULT_PATH,
                        help='if provided, crawling results will be loaded and saved to this file, defaults to '
                             f'{DEFAULT_PATH}')
    parser_args = parser.parse_args()
    main(**vars(parser_args))
