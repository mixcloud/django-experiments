import re
from distutils.core import setup
from setuptools import find_packages

# http://bugs.python.org/issue15881
try:
    import multiprocessing
except ImportError:
    pass


def parse_requirements(file_name):
    requirements = []
    for line in open(file_name, 'r').read().split('\n'):
        if re.match(r'(\s*#)|(\s*$)', line):
            continue
        if re.match(r'\s*-e\s+', line):
            requirements.append(re.sub(r'\s*-e\s+.*#egg=(.*)$', r'\1', line))
        elif re.match(r'\s*-f\s+', line):
            pass
        else:
            requirements.append(line)

    return requirements


def parse_dependency_links(file_name):
    dependency_links = []
    for line in open(file_name, 'r').read().split('\n'):
        if re.match(r'\s*-[ef]\s+', line):
            dependency_links.append(re.sub(r'\s*-[ef]\s+', '', line))

    return dependency_links


setup(
    name='django-experiments',
    version='0.3.5b',
    description='Python Django AB Testing Framework',
    author='Chris Villa, Roberto Barreda',
    author_email='chris@mixcloud.com, roberto.barreda@gmail.com',
    url='https://github.com/robertobarreda/django-experiments',
    packages=find_packages(exclude=["example"]),
    include_package_data=True,
    license="MIT license, see LICENSE file",
    install_requires=parse_requirements('requirements.txt'),
    dependency_links=parse_dependency_links('requirements.txt'),
    long_description=open('README.rst').read(),
    test_suite="testrunner.runtests",
)
