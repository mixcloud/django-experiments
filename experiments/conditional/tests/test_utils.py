# coding=utf-8
from __future__ import absolute_import

from unittest import TestCase

from lxml.etree import XMLSyntaxError

from experiments.tests.testing_2_3 import mock

from experiments.conditional.utils import xml_bool, Experiments


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


class ConditionalEnrollmentTestCase(TestCase):

    def setUp(self):
        self.request = mock.MagicMock()
        self.context = {'request': self.request}
        self.experiments = Experiments(self.context)

    @mock.patch('experiments.utils.participant')
    def test_get_participant(self, participant):
        value = self.experiments.get_participant()
        participant.assert_called_once_with(self.request)
        self.assertEqual(value, participant.return_value)

    def test_report(self):
        instance = mock.MagicMock()
        instance.name = "mock_experiment"
        active = True
        variate = 'mock_variate'
        self.experiments._report(instance, active, variate)
        self.assertIn(
            'mock_experiment', self.experiments.report['auto_enroll'])
        expected_report = {
            'auto-enrolling': True,
            'enrolled_variate': 'mock_variate',
        }
        self.assertEqual(
            expected_report,
            self.experiments.report['auto_enroll']['mock_experiment']
        )

    def test_conditionally_enroll_wo_instances(self):
        self.experiments.instances = []
        with mock.patch.object(self.experiments, 'get_participant'):
            self.experiments.conditionally_enroll()
            self.experiments.get_participant.assert_not_called()
        expected_report = {'auto_enroll': {}}
        self.assertEqual(expected_report, self.experiments.report)

    def test_conditionally_enroll_w_instances(self):
        i1, i2 = mock.MagicMock(), mock.MagicMock()
        i1.name = 'mock_exp_1'
        i2.name = 'mock_exp_2'
        i1.should_auto_enroll.return_value = False
        i2.should_auto_enroll.return_value = True
        participant = mock.MagicMock()
        participant.get_alternative.return_value = 'variate_for_exp_1'
        participant.enroll.return_value = 'variate_for_exp_2'
        self.experiments.instances = [i1, i2]
        with mock.patch.object(self.experiments, 'get_participant'):
            self.experiments.get_participant.return_value = participant
            self.experiments.conditionally_enroll()
            self.assertEquals(self.experiments.get_participant.call_count, 2)
        expected_report = {
            'auto_enroll': {
                'mock_exp_1': {
                    'auto-enrolling': False,
                    'enrolled_variate': 'variate_for_exp_1',
                },
                'mock_exp_2': {
                    'auto-enrolling': True,
                    'enrolled_variate': 'variate_for_exp_2',
                },
            },
        }
        self.assertEqual(expected_report, self.experiments.report)
