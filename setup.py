#!/usr/bin/env python
from setuptools import setup, find_packages

__doc__="""
Generic Template Finder Middleware for Django
"""

version = '0.0.3'

setup(name='django-gtf',
    version=version,
    description='Generit Template Finder Middleware for Django',
    author='Fusionbox programmers',
    author_email='programmers@fusionbox.com',
    keywords='django boilerplate',
    long_description=__doc__,
    url='https://github.com/fusionbox/django-gtf',
    packages=find_packages(),
    package_data={},
    namespace_packages=[],
    platforms = "any",
    license='BSD',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
    ],
    install_requires = ['six'],
    requires = ['six'],
)
