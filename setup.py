from setuptools import setup, find_packages

with open('requirements.txt', 'r+') as requirements_file:
    requirements = requirements_file.read().splitlines()

setup(
    name='Parallel Web Crawler',
    version='2.1',
    description='Crawls the web, like a spider. Uses threads, also like a spider.',
    author='Shayaan Syed Ali',
    author_email='shayaan.syed.ali@gmail.com',
    install_requires=requirements,
    packages=find_packages()
)
