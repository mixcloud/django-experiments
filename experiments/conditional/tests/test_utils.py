# coding=utf-8
from __future__ import absolute_import

from unittest import TestCase

from lxml.etree import XMLSyntaxError

from experiments.conditional.utils import xml_bool


class XmlParserTestCase(TestCase):

    def test_empty(self):
        with self.assertRaises(XMLSyntaxError):
            xml_bool('')

    def test_simple_true(self):
        content = '<true />'
        value = xml_bool(content)
        self.assertTrue(value)

    def test_simple_false(self):
        content = '<false />'
        value = xml_bool(content)
        self.assertFalse(value)

    def test_unknown(self):
        content = '<dmfdmfd />'
        with self.assertRaises(ValueError):
            xml_bool(content)

    def test_any_true(self):
        content = '''
        <any_of>
        <false />
        <true />
        <false />
        </any_of>
        '''
        value = xml_bool(content)
        self.assertTrue(value)

    def test_any_only_true(self):
        content = '''
        <any_of>
        <true />
        <true />
        <true />
        </any_of>
        '''
        value = xml_bool(content)
        self.assertTrue(value)

    def test_any_false(self):
        content = '''
        <any_of>
        <false />
        <false />
        </any_of>
        '''
        value = xml_bool(content)
        self.assertFalse(value)

    def test_any_empty(self):
        content = '''
        <any_of>
        </any_of>
        '''
        value = xml_bool(content)
        self.assertFalse(value)

    def test_all_true(self):
        content = '''
        <all_of>
        <true/>
        </all_of>
        '''
        value = xml_bool(content)
        self.assertTrue(value)

    def test_all_true_many(self):
        content = '''
        <all_of>
        <true/>
        <true/>
        <true/>
        </all_of>
        '''
        value = xml_bool(content)
        self.assertTrue(value)

    def test_all_many_true_one_false(self):
        content = '''
        <all_of>
        <true/>
        <true/>
        <false/>
        <true/>
        </all_of>
        '''
        value = xml_bool(content)
        self.assertFalse(value)

    def test_all_empty(self):
        content = '''
        <all_of>
        </all_of>
        '''
        value = xml_bool(content)
        self.assertFalse(value)

    def test_deep_nested_stuff(self):
        content = '''
        <all_of>
          <true/>
          <true/>
          <any_of>
            <false/>
            <true/>
            <any_of>
              <true />
            </any_of>
            <all_of>
              <all_of>
                <all_of>
                  <any_of>
                    <false/>                
                    <true />                
                    <false/>                
                  </any_of>                
                </all_of>
              </all_of>
            </all_of>
          </any_of>
          <true/>
        </all_of>
        '''
        value = xml_bool(content)
        self.assertTrue(value)
