# Parallel Web Crawler

```
usage: crawler.py [-h] [-s START_URL] [-t THREAD_LIMIT] [-p PATH]

Crawls the web, like a spider. Uses threads, also like a spider.

optional arguments:
  -h, --help            show this help message and exit
  -s START_URL, --start-url START_URL
                        the starting point of the crawl, defaults to
                        https://www.wikipedia.org/
  -t THREAD_LIMIT, --thread-limit THREAD_LIMIT
                        the number of threads to use when crawling, defaults to 4
  -p PATH, --path PATH  if provided, crawling results will be loaded and saved to this file,
                        defaults to web.save
```
