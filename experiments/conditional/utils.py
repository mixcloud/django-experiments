# coding=utf-8
import lxml


def xml_bool(xml_str):
    xml_tree = lxml.etree.XML(xml_str)
    return parse_recursive(xml_tree)


def parse_recursive(elem):
    if elem.tag == 'true':
        return True
    if elem.tag == 'false':
        return False
    if elem.tag == 'any_of':
        return any(map(parse_recursive, elem.getchildren()))
    if elem.tag == 'all_of':
        return all(map(parse_recursive, elem.getchildren()))
    raise ValueError('unknown tag: {}'.format(elem))
