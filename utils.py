import pickle
import queue


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
