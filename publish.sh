#!/usr/bin/env bash

rm dist/*
python setup.py bdist_wheel --universal
twine upload --repository-url https://upload.pypi.org/legacy/ dist/consumeraffairs_django_experiments-*.whl
