from urllib import request
from http import client
from html import parser
import queue
import threading
import time
    

class PageParserError(ValueError):
    """Raised when an HTML page cannot be parsed"""
    

class URLExtractor(parser.HTMLParser):
    
    def __init__(self, data):
        super().__init__()
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
                self._found_links.add(val)
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
    url_extractor = URLExtractor(body.decode())
    return url_extractor.links()


def crawl(url, url_graph, url_graph_lock):
    
    linked_urls = urls_on_page(url)

    with url_graph_lock:
        url_graph[url] = linked_urls
        return [linked_url for linked_url in linked_urls if linked_url not in url_graph]


_print_lock = threading.Lock()


def locked_print(msg, *args, **kwargs):
    with _print_lock:
        print(msg, *args, **kwargs)


def crawl_worker_task(url_queue: queue.Queue, url_graph, url_graph_lock):
    while True:
        url = url_queue.get()
        locked_print(f'Crawling {url}')
        try:
            linked_urls = crawl(url, url_graph, url_graph_lock)
            locked_print(f'Finished crawling {url}')
            with url_graph_lock:
                url_graph[url] = linked_urls
            for linked_url in linked_urls:
                url_queue.put(linked_url)
        except Exception as e:
            locked_print(f'Failed to crawl {url}, encountered {e}')

    
def main(start_url, thread_limit, ):
    url_queue = queue.Queue()
    url_queue.put(start_url)
    url_graph = dict()
    urls_graph_lock = threading.Lock()
    
    threads = [threading.Thread(target=crawl_worker_task, args=(url_queue, url_graph, urls_graph_lock), daemon=True)
               for _ in range(thread_limit)]
    
    for thread in threads:
        thread.start()
        
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    
    # TODO:
    #   - Visualization
    #   - Serialization


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Crawls the web')
    parser.add_argument('-s', '--start-url', default=r'https://www.wikipedia.org/',
                        help='the starting point of the crawl')
    parser.add_argument('-t', '--thread-limit', default=4,
                        help='the number of threads to use when crawling')
    parser_args = parser.parse_args()
    main(**vars(parser_args))
