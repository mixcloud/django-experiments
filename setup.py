import codecs  # to use a consistent encoding
from os import path
from setuptools import setup, find_packages  # prefer setuptools over distutils


# Get the long description from the README file
PATH = path.abspath(path.dirname(__file__))
with codecs.open(path.join(PATH, 'README.rst'), encoding='utf-8') as f:
    LONG_DESCRIPTION = f.read()

setup(
    name='django-experiments',
    version='1.2.0',
    description='Python Django AB Testing Framework',
    long_description=LONG_DESCRIPTION,
    author='Mixcloud',
    author_email='technical@mixcloud.com',
    url='https://github.com/mixcloud/django-experiments',
    packages=find_packages(exclude=["example_project"]),
    include_package_data=True,
    license='MIT',
    install_requires=[
        'django>=1.7.0',
        'django-modeldict-yplan>=1.5.0',
        'jsonfield>=1.0.3',
        'redis>=2.4.9',
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
        'Programming Language :: Python :: 2 :: Only',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Framework :: Django',
        'Framework :: Django :: 1.7',
        'Framework :: Django :: 1.8',
        'Framework :: Django :: 1.9',
        'Framework :: Django :: 1.10',
        'Framework :: Django :: 1.11',
    ],
)
