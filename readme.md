# Parallel Web Crawler

A simple web crawler.

Please open an issue on Github if you encounter errors or would like to
request a feature.

This implementation crawls absolute and relative URLs.

## Installation
1. Install Python 3.7.x.
2. Clone the repository.
3. Open the repository's root folder in a terminal.
4. Run `python .\setup.py install` to install dependencies.

## Usage

`
python .\crawler.py [origin_url [output_file_name [statistics_file_name
[max_n_links [timeout [max_n_threads]]]]]]
`

Default values:
* origin = 'https://www.wikipedia.org/'
* output_file_name = 'graph.out'
* statistics_file_name = 'stats.out'
* max_n_links = 100
* timeout = 60
* max_n_threads = 10

### Examples

Do a web crawl outward from Wikipedia:

`python .\crawler.py http://wikipedia.com`

Web crawl outwards from http://example.com, outputting the results to
example-crawl.txt, outputting the statistics to example-stats.txt,
traversing at most 20 links, with a timeout of 120 seconds, spawning at
most 5 threads to crawl.

`python .\crawler.py http://example.com/ example-crawl.txt
example-stats.txt 20 120 5`
