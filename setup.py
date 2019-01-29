from setuptools import setup, find_packages

setup(
    name='Parallel Web Crawler',
    version='1.0',
    description='A web crawler for CS 4438 at the University of Western Ontario',
    author='Shayaan Syed Ali',
    author_email='shayaan.syed.ali@gmail.com',
    install_requires=[
        'scrapy',
        'validators',
        'lxml',
        'requests'
    ],
    packages=find_packages()
)
