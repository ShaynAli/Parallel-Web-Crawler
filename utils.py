import pickle
import queue
import threading
import functools
import sys
import os


ENABLE_CONSOLE_COLOURS = True


def yield_from_queue(q, timeout=None):
    while not q.empty():
        yield q.get(timeout=timeout)


def save(url_queue, url_graph, filepath):
    url_list = list(yield_from_queue(url_queue))
    with open(filepath, 'wb') as file:
        pickle.dump((url_list, url_graph), file)


def load(filepath):
    with open(filepath, 'rb') as file:
        url_list, url_graph = pickle.load(file)
    url_queue = queue.Queue()
    for url in url_list:
        url_queue.put(url)
    return url_queue, url_graph


if sys.platform.lower() == "win32":
    os.system('color')


class PrintColours:
    END = '\033[0m'
    INFO = '\033[94m'
    GOOD = '\033[92m'
    WARNING = '\033[93m'
    ERROR = '\033[91m'


_print_lock = threading.Lock()


def sync_print(msg, print_colour=None, *args, **kwargs):
    if print_colour and ENABLE_CONSOLE_COLOURS:
        msg = f'{print_colour}{msg}{PrintColours.END}'
    with _print_lock:
        print(msg, *args, **kwargs)


info_sync_print = functools.partial(sync_print, print_colour=PrintColours.INFO)
good_sync_print = functools.partial(sync_print, print_colour=PrintColours.GOOD)
warning_sync_print = functools.partial(sync_print, print_colour=PrintColours.WARNING)
error_sync_print = functools.partial(sync_print, print_colour=PrintColours.ERROR)
