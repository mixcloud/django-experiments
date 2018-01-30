# coding=utf-8
from django.test import TestCase

from experiments.api.models import RemoteExperiment, RemoteApiException
from experiments.consts import CONTROL_STATE
from experiments.tests.testing_2_3 import mock


class ModelsTestCase(TestCase):

    def setUp(self):
        self.batch = 14
        if not RemoteExperiment.objects.exists():
            RemoteExperiment.objects.create(
                state=CONTROL_STATE,
            )
        RemoteExperiment.objects.update(batch=self.batch)

    @mock.patch('experiments.api.models.Lock')
    @mock.patch('experiments.api.models.RemoteExperiment._update_remotes')
    def test_update_remotes(self, _update_remotes, lock_class):
        mock_lock = lock_class.return_value
        mock_lock.acquire.return_value = True
        mock_remote_data = ('error 1', 'error 2',)
        _update_remotes.return_value = mock_remote_data

        value = RemoteExperiment.update_remotes()

        self.assertEqual(list(value), list(mock_remote_data))
        _update_remotes.assert_called_with(mock_lock)
        lock_class.assert_called_once_with(
            'fetching_remote_experiments')
        mock_lock.acquire.assert_called_once_with(blocking=False)
        mock_lock.release.assert_called_once_with()

    @mock.patch('experiments.api.models.Lock')
    @mock.patch('experiments.api.models.RemoteExperiment._update_remotes')
    def test_wait_for_another_thread_to_update_remotes(
            self, _update_remotes, lock_class):
        mock_lock = lock_class.return_value
        mock_lock.acquire.return_value = False

        value = RemoteExperiment.update_remotes()

        self.assertEqual(list(value), [])
        _update_remotes.assert_not_called()
        lock_class.assert_called_once_with(
            'fetching_remote_experiments')
        mock_lock.acquire.assert_has_calls(
            (mock.call(blocking=False), mock.call(blocking=True)))
        mock_lock.release.assert_called_once_with()

    @mock.patch('experiments.api.models.conf')
    def test_update_remotes_wo_remotes(self, patched_conf):
        patched_conf.API['remotes'] = []
        mock_lock = mock.MagicMock()

        value = RemoteExperiment._update_remotes(mock_lock)

        self.assertEqual(list(value), [])
        mock_lock.extend.assert_not_called()

    @mock.patch(
        'experiments.api.models.RemoteExperiment._fetch_remote_instances')
    @mock.patch(
        'experiments.api.models.RemoteExperiment.objects.update_or_create')
    @mock.patch('experiments.api.models.logger')
    @mock.patch('experiments.api.models.conf')
    def test_update_remotes_w_remotes(
            self, patched_conf, logger, update_or_create,
            _fetch_remote_instances):
        mock_server_config = {
            'url': 'some_url',
            'token': 'some_token',
        }
        patched_conf.API = {'remotes': [mock_server_config]}
        mock_lock = mock.MagicMock()
        mock_instance = {
            'name': 'mock remote name',
            'url': 'mock remote url',
            'admin_url': 'mock remote admin_url',
            'start_date': 'mock remote start_date',
            'end_date': 'mock remote end_date',
            'state': 'mock remote state',
            'statistics': 'mock remote statistics',
            'alternatives_list': 'mock remote alternatives_list',
        }
        mock_site = {
            'name': 'mock site name',
        }
        _fetch_remote_instances.return_value = [(mock_instance, mock_site),]
        local_mock_instance = mock.MagicMock()
        created = True
        update_or_create.return_value = (local_mock_instance, created)

        value = RemoteExperiment._update_remotes(mock_lock)

        self.assertEqual(list(value), [])
        logger.warning.assert_not_called()
        logger.exception.assert_not_called()
        mock_lock.extend.assert_called_once_with(
            timeout=RemoteExperiment.MAX_WAIT_REMOTE_SYNC)
        update_or_create.assert_called_once_with(
            site='mock site name',
            name='mock remote name',
            defaults={
                'url': 'mock remote url',
                'admin_url': 'mock remote admin_url',
                'start_date': 'mock remote start_date',
                'end_date': 'mock remote end_date',
                'state': 'mock remote state',
                'statistics': 'mock remote statistics',
                'alternatives_list': 'mock remote alternatives_list',
                'batch': self.batch + 1,
            },
        )

    @mock.patch(
        'experiments.api.models.RemoteExperiment._fetch_remote_instances')
    @mock.patch(
        'experiments.api.models.RemoteExperiment.objects.update_or_create')
    @mock.patch('experiments.api.models.logger')
    @mock.patch('experiments.api.models.conf')
    def test_update_remotes_w_remotes_wo_instances(
            self, patched_conf, logger, update_or_create,
            _fetch_remote_instances):
        mock_server_config = {
            'url': 'some_url',
            'token': 'some_token',
        }
        patched_conf.API = {'remotes': [mock_server_config]}
        mock_lock = mock.MagicMock()

        _fetch_remote_instances.return_value = []
        local_mock_instance = mock.MagicMock()
        created = True
        update_or_create.return_value = (local_mock_instance, created)

        value = RemoteExperiment._update_remotes(mock_lock)

        self.assertEqual(list(value), [])
        logger.warning.assert_not_called()
        logger.exception.assert_not_called()
        mock_lock.extend.assert_called_once_with(
            timeout=RemoteExperiment.MAX_WAIT_REMOTE_SYNC)
        update_or_create.assert_not_called()

    @mock.patch(
        'experiments.api.models.RemoteExperiment._fetch_remote_instances')
    @mock.patch(
        'experiments.api.models.RemoteExperiment.objects.update_or_create')
    @mock.patch('experiments.api.models.logger')
    @mock.patch('experiments.api.models.conf')
    def test_update_remotes_w_remotes_lock_stuk(
            self, patched_conf, logger, update_or_create,
            _fetch_remote_instances):
        mock_server_config = {
            'url': 'some_url',
            'token': 'some_token',
        }
        patched_conf.API = {'remotes': [mock_server_config]}
        mock_lock = mock.MagicMock()
        mock_lock.extend.return_value = False

        _fetch_remote_instances.return_value = []
        local_mock_instance = mock.MagicMock()
        created = True
        update_or_create.return_value = (local_mock_instance, created)

        value = RemoteExperiment._update_remotes(mock_lock)

        self.assertEqual(list(value), [])
        self.assertEqual(1, logger.warning.call_count)
        self.assertIn(
            "Server too slow or lock to short!",
            logger.warning.call_args_list[0][0][0]
        )
        logger.exception.assert_not_called()
        mock_lock.extend.assert_called_once_with(
            timeout=RemoteExperiment.MAX_WAIT_REMOTE_SYNC)
        update_or_create.assert_not_called()

    @mock.patch(
        'experiments.api.models.RemoteExperiment._fetch_remote_instances')
    @mock.patch(
        'experiments.api.models.RemoteExperiment.objects.update_or_create')
    @mock.patch('experiments.api.models.logger')
    @mock.patch('experiments.api.models.conf')
    def test_update_remotes_but_omg_exception(
            self, patched_conf, logger, update_or_create,
            _fetch_remote_instances):
        mock_server_config = {
            'url': 'some_url',
            'token': 'some_token',
        }
        patched_conf.API = {'remotes': [mock_server_config]}
        mock_lock = mock.MagicMock()
        _fetch_remote_instances.side_effect = ValueError('OMG Exception!')

        value = RemoteExperiment._update_remotes(mock_lock)
        value = list(value)

        self.assertEqual(len(value), 1)
        exc = value[0]
        self.assertIsInstance(exc, RemoteApiException)
        self.assertIn('OMG Exception!', repr(exc))
        logger.warning.assert_not_called()
        logger.exception.assert_called_once_with(
            'Failed updating from remote experiments API')
        mock_lock.extend.assert_called_once_with(
            timeout=RemoteExperiment.MAX_WAIT_REMOTE_SYNC)
        update_or_create.assert_not_called()

    @mock.patch('experiments.api.models.requests')
    def test_fetch_remote_instaces(self, requests):
        mock_responses = [
            {
                "site": {
                    "name": "Test Site"
                },
                "count": 2,
                "next": 'url_for_page_2',
                "previous": None,
                "results": [
                    {'result': 1},
                    {'result': 2},
                ],
            },
            {
                "site": {
                    "name": "Test Site"
                },
                "count": 1,
                "next": None,
                "previous": 'url_for_page_1',
                "results": [
                    {'result': 3},
                ],
            },
        ]
        response = requests.get.return_value
        response.json.side_effect = mock_responses
        value = RemoteExperiment._fetch_remote_instances(
            {'url': 'url_for_page_1', 'token': 'mock_token'})
        expected_result = [
            ({'result': 1}, {'name': 'Test Site'}),
            ({'result': 2}, {'name': 'Test Site'}),
            ({'result': 3}, {'name': 'Test Site'}),
        ]
        self.assertEqual(list(value), expected_result)

    def test_remote_payload(self):
        instance = RemoteExperiment(state=3)
        expected = {'state': 3}
        self.assertEqual(instance.remote_payload, expected)

    @mock.patch('experiments.api.models.conf')
    def test_remote_token(self, conf):
        conf.API = {
            'remotes': [
                {'url': 'url1', 'token': 'token1'},
                {'url': 'url2', 'token': 'token2'},
                {'url': 'url3', 'token': 'token3'},
            ]
        }
        instance = RemoteExperiment(url='url2222')
        self.assertEqual(instance.remote_token, 'token2')

    @mock.patch('experiments.api.models.conf')
    def test_remote_token_unknown(self, conf):
        conf.API = {
            'remotes': [
                {'url': 'url1', 'token': 'token1'},
                {'url': 'url2', 'token': 'token2'},
                {'url': 'url3', 'token': 'token3'},
            ]
        }
        instance = RemoteExperiment(url='url7777')
        self.assertIsNone(instance.remote_token)
