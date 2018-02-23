# -*- coding: utf-8 -*-
from experiments.conf import USE_DJANGO_SUIT


def experiments(request):
    """To check if django suit is used"""
    return {'use_django_suit': USE_DJANGO_SUIT}
