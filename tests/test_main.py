import json
import os.path
import shutil
import sys
import unittest
from io import TextIOWrapper

from framework.alias import StartResponse


class DummyStartResponse(StartResponse):
    __slots__ = ('status', 'headers')

    def __call__(self, *args):
        self.status, self.headers = args


class TestMain(unittest.TestCase):
    def setUp(self):
        from framework.main import Main

        self.app, self.root_path = Main, os.path.dirname(sys.modules[__name__].__file__)
        self.folder = os.path.join(self.root_path, 'static')

    def test_no_folder(self):
        if os.path.isdir(self.folder):
            shutil.rmtree(self.folder)

        app = self.app(__name__)

        self.assertFalse(app.isdir)

        with self.assertRaises(AttributeError):
            app.__getattribute__('url')

        with self.assertRaises(AttributeError):
            app.__getattribute__('folder')

        with self.assertRaises(AttributeError):
            app.__getattribute__('encoding')

    def test_attribute(self):
        os.makedirs(
            path_folder := os.path.abspath(os.path.join(self.root_path, 'path/static/folder')),
            exist_ok=True
        )

        app = self.app(__name__, '/', 'path/static/folder', 'ascii')

        self.assertEqual('/', app.url)
        self.assertEqual(path_folder, app.folder)
        self.assertEqual('ascii', app.encoding)

        app = self.app(__name__, static_folder=path_folder)

        self.assertEqual(path_folder, app.folder)

        shutil.rmtree(os.path.join(self.root_path, 'path'))

        os.mkdir(self.folder)

        app = self.app(__name__)

        self.assertEqual('/static/', app.url)
        self.assertEqual(self.folder, app.folder)
        self.assertEqual('utf-8', app.encoding)

        with self.assertRaises(ValueError) as context:
            self.app(__name__, slash := 'slash/')

        self.assertTupleEqual(
            ValueError("URL for static files must begin with a slash: '%s'" % slash).args,
            context.exception.args
        )

        with self.assertRaises(ValueError) as context:
            self.app(__name__, slash := '/slash')

        self.assertTupleEqual(
            ValueError("URL for static files must end with a slash: '%s'" % slash).args,
            context.exception.args
        )

    def test_file(self):
        app = self.app(__name__, '/')

        self.assertIsNone(app.file({'PATH_INFO': '/test.no.file'}))

        with open(file := os.path.join(self.folder, 'test.file'), 'w'):
            pass

        self.assertEqual(file, app.file({'PATH_INFO': '/test.file'}))

    def test_wsgi_static(self):
        def file_wrapper(file: TextIOWrapper):
            read = file.read()
            file.close()
            return read

        app = self.app(__name__, '/')

        with open(os.path.join(self.folder, 'test.json'), 'w') as f:
            f.write(json.dumps({'key': 'value'}))

        environ = {'PATH_INFO': '/test.json', 'wsgi.file_wrapper': file_wrapper}

        body = app.file_wrapper(app.file(environ), environ, dummy := DummyStartResponse())

        self.assertDictEqual({'key': 'value'}, json.loads(body))
        self.assertEqual('200 OK', dummy.status)
        self.assertListEqual([('content-type', 'application/json')], dummy.headers)

        environ['PATH_INFO'] = '/test.txt'

        with open(os.path.join(self.folder, 'test.txt'), 'w'):
            pass

        body = app.file_wrapper(app.file(environ), environ, dummy := DummyStartResponse())

        self.assertEqual(b'', body)
        self.assertEqual('200 OK', dummy.status)
        self.assertEqual('text/plain', dummy.headers[0][1])

        with open(os.path.join(self.folder, 'test.txt'), 'w') as f:
            f.write('simple text')

        body = app.file_wrapper(app.file(environ), environ, dummy := DummyStartResponse())

        self.assertEqual(b'simple text', body)
        self.assertEqual('200 OK', dummy.status)
        self.assertEqual('text/plain; charset=utf-8', dummy.headers[0][1])

        shutil.rmtree(self.folder)

    def test_wsgi_routing(self):
        body = list(self.app(__name__)({'PATH_INFO': '/'}, dummy := DummyStartResponse()))[0]

        self.assertEqual(b'File Server', body)
        self.assertEqual('200 OK', dummy.status)
        self.assertTupleEqual(('content-length', '11'), dummy.headers[0])
        self.assertTupleEqual(('content-type', 'text/plain; charset=utf-8'), dummy.headers[1])

        body = list(self.app(__name__)({'PATH_INFO': '/test.error'}, dummy := DummyStartResponse()))[0]

        self.assertEqual(b'Not Found', body)
        self.assertEqual('404 Not Found', dummy.status)
        self.assertTupleEqual(('content-length', '9'), dummy.headers[0])
        self.assertTupleEqual(('content-type', 'text/plain; charset=utf-8'), dummy.headers[1])


def main_module():
    suite = unittest.TestSuite()

    for test in (
            'test_no_folder',
            'test_attribute',
            'test_file',
            'test_wsgi_static',
            'test_wsgi_routing',
    ):
        suite.addTest(TestMain(test))

    return suite
