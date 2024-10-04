#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import datetime
from http import client as http_client
import io
import os
import shutil
from unittest import mock

from oslo_config import cfg
from oslo_utils import uuidutils
import requests

from ironic.common import exception
from ironic.common.glance_service import image_service as glance_v2_service
from ironic.common import image_service
from ironic.tests import base


class HttpImageServiceTestCase(base.TestCase):
    def setUp(self):
        super(HttpImageServiceTestCase, self).setUp()
        self.service = image_service.HttpImageService()
        self.href = 'https://127.0.0.1:12345/fedora.qcow2'

    @mock.patch.object(os.path, 'exists', autospec=True)
    @mock.patch.object(requests, 'head', autospec=True)
    def test_validate_href_http_scheme(self, head_mock, path_mock):
        self.href = 'http://127.0.0.1:12345/fedora.qcow2'
        response = head_mock.return_value
        response.status_code = http_client.OK
        self.service.validate_href(self.href)
        path_mock.assert_not_called()
        head_mock.assert_called_once_with(self.href, verify=True,
                                          timeout=60, auth=None)
        response.status_code = http_client.NO_CONTENT
        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.validate_href,
                          self.href)
        response.status_code = http_client.BAD_REQUEST
        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.validate_href,
                          self.href)

    @mock.patch.object(requests, 'head', autospec=True)
    def test_validate_href_verify_false(self, head_mock):
        cfg.CONF.set_override('webserver_verify_ca', 'False')

        response = head_mock.return_value
        response.status_code = http_client.OK
        self.service.validate_href(self.href)
        head_mock.assert_called_once_with(self.href, verify=False,
                                          timeout=60, auth=None)
        response.status_code = http_client.NO_CONTENT
        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.validate_href,
                          self.href)
        response.status_code = http_client.BAD_REQUEST
        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.validate_href,
                          self.href)

    @mock.patch.object(requests, 'head', autospec=True)
    def test_validate_href_verify_false_error(self, head_mock):
        cfg.CONF.set_override('webserver_verify_ca', 'False')
        head_mock.side_effect = requests.ConnectionError()
        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.validate_href, self.href)
        head_mock.assert_called_once_with(self.href, verify=False,
                                          timeout=60, auth=None)
        head_mock.side_effect = requests.RequestException()
        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.validate_href, self.href)

    @mock.patch.object(requests, 'head', autospec=True)
    def test_validate_href_verify_true(self, head_mock):
        cfg.CONF.set_override('webserver_verify_ca', 'True')

        response = head_mock.return_value
        response.status_code = http_client.OK
        self.service.validate_href(self.href)
        head_mock.assert_called_once_with(self.href, verify=True,
                                          timeout=60, auth=None)
        response.status_code = http_client.NO_CONTENT
        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.validate_href,
                          self.href)
        response.status_code = http_client.BAD_REQUEST
        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.validate_href,
                          self.href)

    @mock.patch.object(requests, 'head', autospec=True)
    def test_validate_href_verify_true_error(self, head_mock):
        cfg.CONF.set_override('webserver_verify_ca', 'True')

        head_mock.side_effect = requests.ConnectionError()
        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.validate_href, self.href)
        head_mock.assert_called_once_with(self.href, verify=True,
                                          timeout=60, auth=None)
        head_mock.side_effect = requests.RequestException()
        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.validate_href, self.href)

    @mock.patch.object(requests, 'head', autospec=True)
    def test_validate_href_verify_valid_path(self, head_mock):
        cfg.CONF.set_override('webserver_verify_ca', '/some/path')

        response = head_mock.return_value
        response.status_code = http_client.OK

        self.service.validate_href(self.href)
        head_mock.assert_called_once_with(self.href, verify='/some/path',
                                          timeout=60, auth=None)
        response.status_code = http_client.NO_CONTENT
        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.validate_href,
                          self.href)
        response.status_code = http_client.BAD_REQUEST
        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.validate_href,
                          self.href)

    @mock.patch.object(requests, 'head', autospec=True)
    def test_validate_href_valid_path_valid_basic_auth(self, head_mock):
        cfg.CONF.set_override('webserver_verify_ca', '/some/path')
        cfg.CONF.set_override('image_server_auth_strategy',
                              'http_basic',
                              'deploy')
        cfg.CONF.set_override('image_server_user', 'test', 'deploy')
        cfg.CONF.set_override('image_server_password', 'test', 'deploy')
        user = cfg.CONF.deploy.image_server_user
        password = cfg.CONF.deploy.image_server_password
        auth_creds = requests.auth.HTTPBasicAuth(user, password)
        response = head_mock.return_value
        response.status_code = http_client.OK

        self.service.validate_href(self.href)
        head_mock.assert_called_once_with(self.href, verify='/some/path',
                                          timeout=60, auth=auth_creds)
        response.status_code = http_client.NO_CONTENT
        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.validate_href,
                          self.href)
        response.status_code = http_client.BAD_REQUEST
        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.validate_href,
                          self.href)

    @mock.patch.object(requests, 'head', autospec=True)
    def test_validate_href_valid_path_invalid_basic_auth(self, head_mock):
        cfg.CONF.set_override('webserver_verify_ca', '/some/path')
        cfg.CONF.set_override('image_server_auth_strategy',
                              'http_basic',
                              'deploy')

        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.validate_href,
                          self.href)

    @mock.patch.object(requests, 'head', autospec=True)
    def test_validate_href_custom_timeout(self, head_mock):
        cfg.CONF.set_override('webserver_connection_timeout', 15)

        response = head_mock.return_value
        response.status_code = http_client.OK
        self.service.validate_href(self.href)
        head_mock.assert_called_once_with(self.href, verify=True,
                                          timeout=15, auth=None)
        response.status_code = http_client.NO_CONTENT
        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.validate_href,
                          self.href)
        response.status_code = http_client.BAD_REQUEST
        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.validate_href,
                          self.href)

    @mock.patch.object(requests, 'head', autospec=True)
    def test_validate_href_verify_connect_error(self, head_mock):
        cfg.CONF.set_override('webserver_verify_ca', '/some/path')
        response = mock.Mock()
        response.status_code = http_client.OK
        head_mock.side_effect = requests.ConnectionError()

        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.validate_href, self.href)
        head_mock.assert_called_once_with(self.href, verify='/some/path',
                                          timeout=60, auth=None)

    @mock.patch.object(requests, 'head', autospec=True)
    def test_validate_href_verify_error(self, head_mock):
        cfg.CONF.set_override('webserver_verify_ca', '/some/path')
        head_mock.side_effect = requests.RequestException()
        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.validate_href, self.href)
        head_mock.assert_called_once_with(self.href, verify='/some/path',
                                          timeout=60, auth=None)

    @mock.patch.object(requests, 'head', autospec=True)
    def test_validate_href_verify_os_error(self, head_mock):
        cfg.CONF.set_override('webserver_verify_ca', '/some/path')
        head_mock.side_effect = OSError()
        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.validate_href, self.href)
        head_mock.assert_called_once_with(self.href, verify='/some/path',
                                          timeout=60, auth=None)

    @mock.patch.object(requests, 'head', autospec=True)
    def test_validate_href_error_with_secret_parameter(self, head_mock):
        cfg.CONF.set_override('webserver_verify_ca', 'False')
        head_mock.return_value.status_code = 204
        e = self.assertRaises(exception.ImageRefValidationFailed,
                              self.service.validate_href,
                              self.href,
                              True)
        self.assertIn('secreturl', str(e))
        self.assertNotIn(self.href, str(e))
        head_mock.assert_called_once_with(self.href, verify=False,
                                          timeout=60, auth=None)

    @mock.patch.object(requests, 'head', autospec=True)
    def test_validate_href_path_forbidden(self, head_mock):
        cfg.CONF.set_override('webserver_verify_ca', 'True')

        response = head_mock.return_value
        response.status_code = http_client.FORBIDDEN
        url = self.href + '/'
        resp = self.service.validate_href(url)
        head_mock.assert_called_once_with(url, verify=True,
                                          timeout=60, auth=None)
        self.assertEqual(http_client.FORBIDDEN, resp.status_code)

    @mock.patch.object(requests, 'head', autospec=True)
    def test_validate_href_path_redirected(self, head_mock):
        cfg.CONF.set_override('webserver_verify_ca', 'True')

        response = head_mock.return_value
        response.status_code = http_client.MOVED_PERMANENTLY
        url = self.href + '/'
        new_url = 'http://new-url'
        response.headers = {'location': new_url}
        exc = self.assertRaises(exception.ImageRefIsARedirect,
                                self.service.validate_href,
                                url)
        self.assertEqual(new_url, exc.redirect_url)
        head_mock.assert_called_once_with(url, verify=True,
                                          timeout=60, auth=None)

    def test_verify_basic_auth_cred_format(self):
        self.assertIsNone(self
                          .service
                          .verify_basic_auth_cred_format(self.href,
                                                         "SpongeBob",
                                                         "SquarePants"))

    def test_verify_basic_auth_cred_format_empty_user(self):
        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.verify_basic_auth_cred_format,
                          self.href,
                          "",
                          "SquarePants")

    def test_verify_basic_auth_cred_format_empty_password(self):
        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.verify_basic_auth_cred_format,
                          self.href,
                          "SpongeBob",
                          "")

    def test_verify_basic_auth_cred_format_none_user(self):
        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.verify_basic_auth_cred_format,
                          self.href,
                          None,
                          "SquarePants")

    def test_verify_basic_auth_cred_format_none_password(self):
        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.verify_basic_auth_cred_format,
                          self.href,
                          "SpongeBob",
                          None)

    def test_gen_auth_from_conf_user_pass_success(self):
        cfg.CONF.set_override('image_server_auth_strategy',
                              'http_basic',
                              'deploy')
        cfg.CONF.set_override('image_server_password', 'SpongeBob', 'deploy')
        cfg.CONF.set_override('image_server_user', 'SquarePants', 'deploy')
        correct_auth = \
            requests.auth.HTTPBasicAuth('SquarePants',
                                        'SpongeBob')
        return_auth = \
            self.service.gen_auth_from_conf_user_pass(self.href)
        self.assertEqual(correct_auth, return_auth)

    def test_gen_auth_from_conf_user_pass_none(self):
        cfg.CONF.set_override('image_server_auth_strategy', 'noauth', 'deploy')
        cfg.CONF.set_override('image_server_password', 'SpongeBob', 'deploy')
        cfg.CONF.set_override('image_server_user', 'SquarePants', 'deploy')
        return_auth = \
            self.service.gen_auth_from_conf_user_pass(self.href)
        self.assertIsNone(return_auth)

    @mock.patch.object(requests, 'head', autospec=True)
    def _test_show(self, head_mock, mtime, mtime_date):
        head_mock.return_value.status_code = http_client.OK
        head_mock.return_value.headers = {
            'Content-Length': 100,
            'Last-Modified': mtime
        }
        result = self.service.show(self.href)
        head_mock.assert_called_once_with(self.href, verify=True,
                                          timeout=60, auth=None)
        self.assertEqual({'size': 100, 'updated_at': mtime_date,
                          'properties': {}, 'no_cache': False}, result)

    def test_show_rfc_822(self):
        self._test_show(mtime='Tue, 15 Nov 2014 08:12:31 GMT',
                        mtime_date=datetime.datetime(2014, 11, 15, 8, 12, 31))

    def test_show_rfc_850(self):
        self._test_show(mtime='Tuesday, 15-Nov-14 08:12:31 GMT',
                        mtime_date=datetime.datetime(2014, 11, 15, 8, 12, 31))

    def test_show_ansi_c(self):
        self._test_show(mtime='Tue Nov 15 08:12:31 2014',
                        mtime_date=datetime.datetime(2014, 11, 15, 8, 12, 31))

    @mock.patch.object(requests, 'head', autospec=True)
    def _test_show_with_cache(self, head_mock, cache_control, no_cache):
        head_mock.return_value.status_code = http_client.OK
        head_mock.return_value.headers = {
            'Content-Length': 100,
            'Last-Modified': 'Tue, 15 Nov 2014 08:12:31 GMT',
            'Cache-Control': cache_control,
        }
        result = self.service.show(self.href)
        head_mock.assert_called_once_with(self.href, verify=True,
                                          timeout=60, auth=None)
        self.assertEqual({
            'size': 100,
            'updated_at': datetime.datetime(2014, 11, 15, 8, 12, 31),
            'properties': {},
            'no_cache': no_cache}, result)

    def test_show_cache_allowed(self):
        self._test_show_with_cache(
            # Just because we cannot have nice things, "no-cache" actually
            # means "cache, but always re-validate".
            cache_control='no-cache, private', no_cache=False)

    def test_show_cache_disabled(self):
        self._test_show_with_cache(
            cache_control='no-store', no_cache=True)

    @mock.patch.object(requests, 'head', autospec=True)
    def test_show_no_content_length(self, head_mock):
        head_mock.return_value.status_code = http_client.OK
        head_mock.return_value.headers = {}
        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.show, self.href)
        head_mock.assert_called_with(self.href, verify=True,
                                     timeout=60, auth=None)

    @mock.patch.object(shutil, 'copyfileobj', autospec=True)
    @mock.patch.object(requests, 'get', autospec=True)
    def test_download_success_http_scheme(self, req_get_mock, shutil_mock):
        self.href = 'http://127.0.0.1:12345/fedora.qcow2'
        response_mock = req_get_mock.return_value
        response_mock.status_code = http_client.OK
        response_mock.raw = mock.MagicMock(spec=io.BytesIO)
        file_mock = mock.Mock(spec=io.BytesIO)
        self.service.download(self.href, file_mock)
        shutil_mock.assert_called_once_with(
            response_mock.raw.__enter__(), file_mock,
            image_service.IMAGE_CHUNK_SIZE
        )
        req_get_mock.assert_called_once_with(self.href, stream=True,
                                             verify=True,
                                             timeout=60, auth=None)

    @mock.patch.object(shutil, 'copyfileobj', autospec=True)
    @mock.patch.object(requests, 'get', autospec=True)
    def test_download_success_verify_false(
            self, req_get_mock, shutil_mock):
        cfg.CONF.set_override('webserver_verify_ca', 'False')
        response_mock = req_get_mock.return_value
        response_mock.status_code = http_client.OK
        response_mock.raw = mock.MagicMock(spec=io.BytesIO)
        file_mock = mock.Mock(spec=io.BytesIO)
        self.service.download(self.href, file_mock)
        shutil_mock.assert_called_once_with(
            response_mock.raw.__enter__(), file_mock,
            image_service.IMAGE_CHUNK_SIZE
        )
        req_get_mock.assert_called_once_with(self.href, stream=True,
                                             verify=False,
                                             timeout=60, auth=None)

    @mock.patch.object(shutil, 'copyfileobj', autospec=True)
    @mock.patch.object(requests, 'get', autospec=True)
    def test_download_success_verify_false_basic_auth_sucess(
            self, req_get_mock, shutil_mock):
        cfg.CONF.set_override('webserver_verify_ca', 'False')
        cfg.CONF.set_override('image_server_auth_strategy',
                              'http_basic',
                              'deploy')
        cfg.CONF.set_override('image_server_user', 'test', 'deploy')
        cfg.CONF.set_override('image_server_password', 'test', 'deploy')
        user = cfg.CONF.deploy.image_server_user
        password = cfg.CONF.deploy.image_server_password
        auth_creds = requests.auth.HTTPBasicAuth(user, password)
        response_mock = req_get_mock.return_value
        response_mock.status_code = http_client.OK
        response_mock.raw = mock.MagicMock(spec=io.BytesIO)
        file_mock = mock.Mock(spec=io.BytesIO)
        self.service.download(self.href, file_mock)
        shutil_mock.assert_called_once_with(
            response_mock.raw.__enter__(), file_mock,
            image_service.IMAGE_CHUNK_SIZE
        )
        req_get_mock.assert_called_once_with(self.href, stream=True,
                                             verify=False, timeout=60,
                                             auth=auth_creds)

    def test_download_success_verify_false_basic_auth_failed(self):
        cfg.CONF.set_override('webserver_verify_ca', 'False')
        cfg.CONF.set_override('image_server_auth_strategy',
                              'http_basic',
                              'deploy')
        file_mock = mock.Mock(spec=io.BytesIO)
        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.download, self.href, file_mock)

    @mock.patch.object(shutil, 'copyfileobj', autospec=True)
    @mock.patch.object(requests, 'get', autospec=True)
    def test_download_success_verify_true(
            self, req_get_mock, shutil_mock):
        cfg.CONF.set_override('webserver_verify_ca', 'True')
        response_mock = req_get_mock.return_value
        response_mock.status_code = http_client.OK
        response_mock.raw = mock.MagicMock(spec=io.BytesIO)
        file_mock = mock.Mock(spec=io.BytesIO)
        self.service.download(self.href, file_mock)
        shutil_mock.assert_called_once_with(
            response_mock.raw.__enter__(), file_mock,
            image_service.IMAGE_CHUNK_SIZE
        )
        req_get_mock.assert_called_once_with(self.href, stream=True,
                                             verify=True,
                                             timeout=60, auth=None)

    @mock.patch.object(shutil, 'copyfileobj', autospec=True)
    @mock.patch.object(requests, 'get', autospec=True)
    def test_download_success_verify_path(
            self, req_get_mock, shutil_mock):
        cfg.CONF.set_override('webserver_verify_ca', '/some/path')
        response_mock = req_get_mock.return_value
        response_mock.status_code = http_client.OK
        response_mock.raw = mock.MagicMock(spec=io.BytesIO)
        file_mock = mock.Mock(spec=io.BytesIO)
        self.service.download(self.href, file_mock)
        shutil_mock.assert_called_once_with(
            response_mock.raw.__enter__(), file_mock,
            image_service.IMAGE_CHUNK_SIZE
        )
        req_get_mock.assert_called_once_with(self.href, stream=True,
                                             verify='/some/path',
                                             timeout=60, auth=None)

    @mock.patch.object(shutil, 'copyfileobj', autospec=True)
    @mock.patch.object(requests, 'get', autospec=True)
    def test_download_fail_verify_false_connerror(
            self, req_get_mock, shutil_mock):
        cfg.CONF.set_override('webserver_verify_ca', False)
        req_get_mock.side_effect = requests.ConnectionError()
        file_mock = mock.Mock(spec=io.BytesIO)
        self.assertRaises(exception.ImageDownloadFailed,
                          self.service.download, self.href, file_mock)

    @mock.patch.object(shutil, 'copyfileobj', autospec=True)
    @mock.patch.object(requests, 'get', autospec=True)
    def test_download_fail_verify_false_ioerror(
            self, req_get_mock, shutil_mock):
        cfg.CONF.set_override('webserver_verify_ca', False)
        response_mock = req_get_mock.return_value
        response_mock.status_code = http_client.OK
        response_mock.raw = mock.MagicMock(spec=io.BytesIO)
        file_mock = mock.Mock(spec=io.BytesIO)
        shutil_mock.side_effect = IOError
        self.assertRaises(exception.ImageDownloadFailed,
                          self.service.download, self.href, file_mock)
        req_get_mock.assert_called_once_with(self.href, stream=True,
                                             verify=False, timeout=60,
                                             auth=None)

    @mock.patch.object(shutil, 'copyfileobj', autospec=True)
    @mock.patch.object(requests, 'get', autospec=True)
    def test_download_success_verify_true_connerror(
            self, req_get_mock, shutil_mock):
        cfg.CONF.set_override('webserver_verify_ca', '/some/path')
        response_mock = mock.Mock()
        response_mock.status_code = http_client.OK
        response_mock.raw = mock.MagicMock(spec=io.BytesIO)
        req_get_mock.side_effect = requests.ConnectionError

        file_mock = mock.Mock(spec=io.BytesIO)
        self.assertRaises(exception.ImageDownloadFailed,
                          self.service.download, self.href, file_mock)
        req_get_mock.assert_called_once_with(self.href, stream=True,
                                             verify='/some/path',
                                             timeout=60, auth=None)

    @mock.patch.object(shutil, 'copyfileobj', autospec=True)
    @mock.patch.object(requests, 'get', autospec=True)
    def test_download_fail_verify_true_ioerror(
            self, req_get_mock, shutil_mock):
        cfg.CONF.set_override('webserver_verify_ca', '/some/path')
        response_mock = req_get_mock.return_value
        response_mock.status_code = http_client.OK
        response_mock.raw = mock.MagicMock(spec=io.BytesIO)
        file_mock = mock.Mock(spec=io.BytesIO)
        shutil_mock.side_effect = IOError
        self.assertRaises(exception.ImageDownloadFailed,
                          self.service.download, self.href, file_mock)
        req_get_mock.assert_called_once_with(self.href, stream=True,
                                             verify='/some/path',
                                             timeout=60, auth=None)

    @mock.patch.object(shutil, 'copyfileobj', autospec=True)
    @mock.patch.object(requests, 'get', autospec=True)
    def test_download_fail_verify_true_oserror(
            self, req_get_mock, shutil_mock):
        cfg.CONF.set_override('webserver_verify_ca', '/some/path')
        response_mock = req_get_mock.return_value
        response_mock.status_code = http_client.OK
        response_mock.raw = mock.MagicMock(spec=io.BytesIO)
        file_mock = mock.Mock(spec=io.BytesIO)
        shutil_mock.side_effect = OSError()
        self.assertRaises(exception.ImageDownloadFailed,
                          self.service.download, self.href, file_mock)
        req_get_mock.assert_called_once_with(self.href, stream=True,
                                             verify='/some/path',
                                             timeout=60, auth=None)

    @mock.patch.object(shutil, 'copyfileobj', autospec=True)
    @mock.patch.object(requests, 'get', autospec=True)
    def test_download_success_custom_timeout(
            self, req_get_mock, shutil_mock):
        cfg.CONF.set_override('webserver_connection_timeout', 15)
        response_mock = req_get_mock.return_value
        response_mock.status_code = http_client.OK
        response_mock.raw = mock.MagicMock(spec=io.BytesIO)
        file_mock = mock.Mock(spec=io.BytesIO)
        self.service.download(self.href, file_mock)
        shutil_mock.assert_called_once_with(
            response_mock.raw.__enter__(), file_mock,
            image_service.IMAGE_CHUNK_SIZE
        )
        req_get_mock.assert_called_once_with(self.href, stream=True,
                                             verify=True,
                                             timeout=15, auth=None)

    @mock.patch.object(requests, 'get', autospec=True)
    def test_get_success(self, req_get_mock):
        response_mock = req_get_mock.return_value
        response_mock.status_code = http_client.OK
        response_mock.text = 'value'
        self.assertEqual('value', self.service.get('http://url'))
        req_get_mock.assert_called_once_with('http://url', stream=False,
                                             verify=True, timeout=60,
                                             auth=None)

    @mock.patch.object(requests, 'get', autospec=True)
    def test_get_handles_exceptions(self, req_get_mock):
        for exc in [OSError, requests.ConnectionError,
                    requests.RequestException, IOError]:
            req_get_mock.reset_mock()
            req_get_mock.side_effect = exc
            self.assertRaises(exception.ImageDownloadFailed,
                              self.service.get,
                              'http://url')
            req_get_mock.assert_called_once_with('http://url', stream=False,
                                                 verify=True, timeout=60,
                                                 auth=None)

    @mock.patch.object(requests, 'get', autospec=True)
    def test_get_success_verify_false(self, req_get_mock):
        cfg.CONF.set_override('webserver_verify_ca', False)
        response_mock = req_get_mock.return_value
        response_mock.status_code = http_client.OK
        response_mock.text = 'value'
        self.assertEqual('value', self.service.get('http://url'))
        req_get_mock.assert_called_once_with('http://url', stream=False,
                                             verify=False, timeout=60,
                                             auth=None)


class FileImageServiceTestCase(base.TestCase):
    def setUp(self):
        super(FileImageServiceTestCase, self).setUp()
        self.service = image_service.FileImageService()
        self.href = 'file:///home/user/image.qcow2'
        self.href_path = '/home/user/image.qcow2'

    @mock.patch.object(os.path, 'isfile', return_value=True, autospec=True)
    def test_validate_href(self, path_exists_mock):
        self.service.validate_href(self.href)
        path_exists_mock.assert_called_once_with(self.href_path)

    @mock.patch.object(os.path, 'isfile', return_value=False, autospec=True)
    def test_validate_href_path_not_found_or_not_file(self, path_exists_mock):
        self.assertRaises(exception.ImageRefValidationFailed,
                          self.service.validate_href, self.href)
        path_exists_mock.assert_called_once_with(self.href_path)

    @mock.patch.object(os.path, 'getmtime', return_value=1431087909.1641912,
                       autospec=True)
    @mock.patch.object(os.path, 'getsize', return_value=42, autospec=True)
    @mock.patch.object(image_service.FileImageService, 'validate_href',
                       autospec=True)
    def test_show(self, _validate_mock, getsize_mock, getmtime_mock):
        _validate_mock.return_value = self.href_path
        result = self.service.show(self.href)
        getsize_mock.assert_called_once_with(self.href_path)
        getmtime_mock.assert_called_once_with(self.href_path)
        _validate_mock.assert_called_once_with(mock.ANY, self.href)
        self.assertEqual({'size': 42,
                          'updated_at': datetime.datetime(2015, 5, 8,
                                                          12, 25, 9, 164191),
                          'properties': {},
                          'no_cache': True}, result)

    @mock.patch.object(shutil, 'copyfile', autospec=True)
    @mock.patch.object(os, 'link', autospec=True)
    @mock.patch.object(os.path, 'realpath', lambda p: p)
    @mock.patch.object(os, 'remove', autospec=True)
    @mock.patch.object(image_service.FileImageService, 'validate_href',
                       autospec=True)
    def test_download_hard_link(self, _validate_mock, remove_mock, link_mock,
                                copy_mock):
        _validate_mock.return_value = self.href_path
        file_mock = mock.Mock(spec=io.BytesIO)
        file_mock.name = 'file'
        self.service.download(self.href, file_mock)
        _validate_mock.assert_called_once_with(mock.ANY, self.href)
        remove_mock.assert_called_once_with('file')
        link_mock.assert_called_once_with(self.href_path, 'file')
        copy_mock.assert_not_called()

    @mock.patch.object(shutil, 'copyfile', autospec=True)
    @mock.patch.object(os, 'link', autospec=True)
    @mock.patch.object(os, 'remove', autospec=True)
    @mock.patch.object(image_service.FileImageService, 'validate_href',
                       autospec=True)
    def test_download_copy(self, _validate_mock, remove_mock, link_mock,
                           copy_mock):
        _validate_mock.return_value = self.href_path
        link_mock.side_effect = PermissionError
        file_mock = mock.MagicMock(spec=io.BytesIO)
        file_mock.name = 'file'
        self.service.download(self.href, file_mock)
        _validate_mock.assert_called_once_with(mock.ANY, self.href)
        link_mock.assert_called_once_with(self.href_path, 'file')
        copy_mock.assert_called_once_with(self.href_path, 'file')

    @mock.patch.object(shutil, 'copyfile', autospec=True)
    @mock.patch.object(os, 'link', autospec=True)
    @mock.patch.object(os.path, 'realpath', autospec=True)
    @mock.patch.object(os, 'remove', autospec=True)
    @mock.patch.object(image_service.FileImageService, 'validate_href',
                       autospec=True)
    def test_download_symlink(self, _validate_mock, remove_mock,
                              realpath_mock, link_mock, copy_mock):
        _validate_mock.return_value = self.href_path
        realpath_mock.side_effect = lambda p: p + '.real'
        file_mock = mock.MagicMock(spec=io.BytesIO)
        file_mock.name = 'file'
        self.service.download(self.href, file_mock)
        _validate_mock.assert_called_once_with(mock.ANY, self.href)
        realpath_mock.assert_called_once_with(self.href_path)
        link_mock.assert_called_once_with(self.href_path + '.real', 'file')
        copy_mock.assert_not_called()

    @mock.patch.object(shutil, 'copyfile', autospec=True)
    @mock.patch.object(os, 'link', autospec=True)
    @mock.patch.object(os, 'remove', autospec=True)
    @mock.patch.object(image_service.FileImageService, 'validate_href',
                       autospec=True)
    def test_download_copy_fail(self, _validate_mock, remove_mock, link_mock,
                                copy_mock):
        _validate_mock.return_value = self.href_path
        link_mock.side_effect = PermissionError
        copy_mock.side_effect = PermissionError
        file_mock = mock.MagicMock(spec=io.BytesIO)
        file_mock.name = 'file'
        self.assertRaises(exception.ImageDownloadFailed,
                          self.service.download, self.href, file_mock)
        _validate_mock.assert_called_once_with(mock.ANY, self.href)
        link_mock.assert_called_once_with(self.href_path, 'file')
        copy_mock.assert_called_once_with(self.href_path, 'file')


class ServiceGetterTestCase(base.TestCase):

    @mock.patch.object(glance_v2_service.GlanceImageService, '__init__',
                       return_value=None, autospec=True)
    def test_get_glance_image_service(self, glance_service_mock):
        image_href = uuidutils.generate_uuid()
        image_service.get_image_service(image_href, context=self.context)
        glance_service_mock.assert_called_once_with(mock.ANY, None,
                                                    self.context)

    @mock.patch.object(glance_v2_service.GlanceImageService, '__init__',
                       return_value=None, autospec=True)
    def test_get_glance_image_service_url(self, glance_service_mock):
        image_href = 'glance://%s' % uuidutils.generate_uuid()
        image_service.get_image_service(image_href, context=self.context)
        glance_service_mock.assert_called_once_with(mock.ANY, None,
                                                    self.context)

    @mock.patch.object(image_service.HttpImageService, '__init__',
                       return_value=None, autospec=True)
    def test_get_http_image_service(self, http_service_mock):
        image_href = 'http://127.0.0.1/image.qcow2'
        image_service.get_image_service(image_href)
        http_service_mock.assert_called_once_with()

    @mock.patch.object(image_service.HttpImageService, '__init__',
                       return_value=None, autospec=True)
    def test_get_https_image_service(self, http_service_mock):
        image_href = 'https://127.0.0.1/image.qcow2'
        image_service.get_image_service(image_href)
        http_service_mock.assert_called_once_with()

    @mock.patch.object(image_service.FileImageService, '__init__',
                       return_value=None, autospec=True)
    def test_get_file_image_service(self, local_service_mock):
        image_href = 'file:///home/user/image.qcow2'
        image_service.get_image_service(image_href)
        local_service_mock.assert_called_once_with()

    def test_get_image_service_invalid_image_ref(self):
        invalid_refs = (
            'usenet://alt.binaries.dvd/image.qcow2',
            'no scheme, no uuid')
        for image_ref in invalid_refs:
            self.assertRaises(exception.ImageRefValidationFailed,
                              image_service.get_image_service, image_ref)
