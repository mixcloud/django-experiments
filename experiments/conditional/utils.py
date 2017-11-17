# coding=utf-8
from lxml import etree


def xml_bool(xml_str):
    xml_tree = etree.XML(xml_str)
    return _parse_recursive(xml_tree)


def _parse_recursive(elem):
    if elem.tag.lower() == 'true':
        return True
    if elem.tag.lower() == 'false':
        return False
    if elem.tag.lower() == 'any_of':
        return any(map(_parse_recursive, elem.getchildren()))
    if elem.tag.lower() == 'all_of':
        children = elem.getchildren()
        if len(children) == 0:
            # # We don't want this:
            # >>> all([])
            # True
            return False
        return all(map(_parse_recursive, children))
    raise ValueError('unknown tag: {}'.format(elem))
