from urllib import request, parse
from http import client
from html import parser
import queue
import threading
import time
import contextlib
import collections

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
            raise URLRetrievalFailure(f'URL returned a non-HTTP response: {response}')
        body = response.read()
    url_extractor = URLExtractor(url=url, data=body.decode())
    return url_extractor.links()


def crawl(url, url_graph):
    """Crawls the given URL and updates the url_graph, uses the url_graph_lock for synchronized access
    :returns All newly found URLs which are not already in the url_graph
    """
    linked_urls = urls_on_page(url)
    url_graph[url] = linked_urls
    return [linked_url for linked_url in linked_urls if linked_url not in url_graph]
    

def crawl_worker(url_boundary_queue, url_graph):
    url = url_boundary_queue.get()
    utils.good_sync_print(f'Crawling {url}')
    try:
        linked_urls = crawl(url, url_graph)
        utils.good_sync_print(f'Finished crawling {url}')
        url_boundary_queue.task_done()
        for linked_url in linked_urls:
            url_boundary_queue.put(linked_url)
    except Exception as e:
        utils.error_sync_print(f'Failed to crawl {url}, encountered {e}')
        raise e
    

class SynchronizedLoopingThread(threading.Thread):
    
    def __init__(self, running_event, target, args=None, kwargs=None, daemon=False, error_cooldown=10):
        super().__init__(target=target, daemon=daemon, args=args or (), kwargs=kwargs or {})
        self.running_event = running_event
        self.error_cooldown = error_cooldown
        
    def run(self):
        while self.running_event.is_set():
            try:
                # This is a looped version of the same invocation which threading.Thread makes and these self.etc
                #   members are populated by the call to super().__init__()
                # noinspection PyUnresolvedReferences
                self._target(*self._args, **self._kwargs)
            except Exception as e:
                utils.error_sync_print(f'{self.__repr__()} encountered {e}')
                time.sleep(self.error_cooldown)
            
            
class SynchronizedDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._item_lock = collections.defaultdict(threading.Lock)
        
    def __setitem__(self, key, value):
        with self.item_lock[key]:
            super().__setitem__(key, value)
        del self.item_lock[key]

    @property
    def item_lock(self):
        try:
            return self._item_lock
        except AttributeError:
            self._item_lock = collections.defaultdict(threading.Lock)
            return self._item_lock
            
    # region Pickle overrides
    
    def __getstate__(self):
        state = vars(self).copy()
        del state['_item_lock']  # Lock objects cannot be Pickled
        return state
        
    def __setstate__(self, state):
        vars(self).update(state)
        
    # endregion

    
def main(start_url, thread_limit, path, colours_disabled):
    
    utils.ENABLE_CONSOLE_COLOURS = not colours_disabled
    
    url_boundary_queue = queue.Queue()
    url_boundary_queue.put(start_url)
    url_graph = SynchronizedDict()
    
    if path:
        with contextlib.suppress(FileNotFoundError, EOFError):
            utils.info_sync_print(f'Loading from {path}')
            url_boundary_queue, url_graph = utils.load(path)
            
    running_event = threading.Event()
    
    threads = [SynchronizedLoopingThread(running_event=running_event,
                                         target=crawl_worker,
                                         args=(url_boundary_queue, url_graph),
                                         daemon=True) for _ in range(int(thread_limit))]
    
    running_event.set()
    for thread in threads:
        thread.start()
        
    try:
        while True:
            time.sleep(10)
            utils.info_sync_print(f'{len(url_graph)} linked crawled')
    except KeyboardInterrupt:
        utils.warning_sync_print('Waiting for threads to finish executing')
        running_event.clear()
        while any(thread.is_alive() for thread in threads):
            continue
    
    if path:
        utils.save(url_boundary_queue, url_graph, path)
        utils.info_sync_print(f'Saved to {path}')

    # TODO:
    #   - Visualization


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Crawls the web, like a spider. Uses threads, also like a spider.')
    parser.add_argument('-s', '--start-url', default=DEFAULT_START_URL,
                        help=f'the starting point of the crawl, defaults to {DEFAULT_START_URL}')
    parser.add_argument('-t', '--thread-limit', default=DEFAULT_THREAD_LIMIT,
                        help=f'the number of threads to use when crawling, defaults to {DEFAULT_THREAD_LIMIT}')
    parser.add_argument('-p', '--path', default=DEFAULT_PATH,
                        help='if provided, crawling results will be loaded and saved to this file, defaults to '
                             f'{DEFAULT_PATH}')
    parser.add_argument('-c', '--colours-disabled', action='store_true',
                        help='if provided, disables colorful console output')
    parser_args = parser.parse_args()
    main(**vars(parser_args))
