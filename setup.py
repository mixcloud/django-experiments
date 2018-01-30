# coding=utf-8
import codecs  # to use a consistent encoding
from os import path
from setuptools import setup, find_packages  # prefer setuptools over distutils


# Get the long description from the README file
PATH = path.abspath(path.dirname(__file__))
with codecs.open(path.join(PATH, 'README.rst'), encoding='utf-8') as f:
    LONG_DESCRIPTION = f.read()

setup(
    name='consumeraffairs-django-experiments',
    version='1.4.2',
    description='Python Django AB Testing Framework',
    long_description=LONG_DESCRIPTION,
    author='ConsumerAffairs',
    author_email='dev@consumeraffairs.com',
    url='https://github.com/ConsumerAffairs/django-experiments',
    packages=find_packages(exclude=["example_project"]),
    include_package_data=True,
    license='MIT',
    install_requires=[
        'django>=1.8,<2',
        'django-modeldict-yplan>=1.5.0',
        'django-jsonfield>=1.0.1',
        'redis>=2.4.9',
        'django-jinja>=2.3.1',
        'django-import-export==0.5.1',
        'six>=1.10.0',
        'lxml>=4.1.1,<5',
        'djangorestframework>=3.6.4,<3.7',
        'requests>2.18,<2.19',
        'Markdown>=2.6.10,<2.7',
    ],
    tests_require=[
        'mock>=1.0.1',
        'tox>=2.3.1',
    ],
    test_suite="testrunner.runtests",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Framework :: Django',
        'Framework :: Django :: 1.8',
        'Framework :: Django :: 1.9',
        'Framework :: Django :: 1.10',
        'Framework :: Django :: 1.11',
    ],
)
