# coding=utf-8
from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from ... import conf
from .serializers import SiteSerializer


class DefaultPaginator(PageNumberPagination):
    page_size = conf.API['local']['page_size']

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('site', SiteSerializer().data),
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data),
        ]))
