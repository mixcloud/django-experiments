#!/usr/bin/env bash

rm -fr dist/*
rm -fr build/*
python setup.py bdist_wheel --universal
twine upload --repository-url https://upload.pypi.org/legacy/ dist/consumeraffairs_django_experiments-*.whl
