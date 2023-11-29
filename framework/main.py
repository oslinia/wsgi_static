import mimetypes
import os.path
import sys
from collections.abc import Iterable

from .alias import StartResponse, WSGIEnvironment, WSGIApplication


def module_path(root_path: str, dirname: str | os.PathLike | None, default: str):
    if dirname is None:
        dirname = default

    return os.path.abspath(os.path.join(root_path, dirname))


class Static:
    __slots__ = ('isdir', 'url', 'folder', 'encoding')

    isdir: bool
    url: str
    folder: str
    encoding: str

    def __init__(self, root_path: str, url: str | None, folder: str | os.PathLike | None, encoding: str | None):
        self.isdir = os.path.isdir(folder := module_path(root_path, folder, 'static'))

        if self.isdir:
            if url is None:
                url = '/static/'

            if not url.startswith('/'):
                raise ValueError(
                    "URL for static files must begin with a slash: '%s'" % url
                )

            if not url.endswith('/'):
                raise ValueError(
                    "URL for static files must end with a slash: '%s'" % url
                )

            for attr, value in (
                    ('url', url),
                    ('folder', folder),
                    ('encoding', 'utf-8' if encoding is None else encoding)
            ):
                setattr(self, attr, value)

    def file(self, environ: WSGIEnvironment):
        if self.isdir and (path_info := environ['PATH_INFO']).startswith(self.url):
            if os.path.isfile(file := os.path.join(self.folder, path_info[len(self.url):])):
                return file

    def file_wrapper(self, file: str, environ: WSGIEnvironment, start_response: StartResponse):
        media_type, encoding = mimetypes.guess_type(file, strict=True)

        if media_type is None:
            media_type = 'text/plain'

        if media_type.startswith('text'):
            if os.path.getsize(file):
                if encoding is None:
                    encoding = self.encoding

                media_type = f"{media_type}{';'} charset={encoding}"

        start_response('200 OK', [('content-type', media_type)])

        return environ['wsgi.file_wrapper'](open(file, 'rb'))


class Routing:
    __slots__ = ('status', 'body')

    def __init__(self, environ: WSGIEnvironment):
        if '/' == environ['PATH_INFO']:
            self.status, self.body = '200 OK', b'File Server'
        else:
            self.status, self.body = '404 Not Found', b'Not Found'

    def __call__(self, start_response: StartResponse):
        start_response(self.status, [
            ('content-length', str(len(self.body))),
            ('content-type', 'text/plain; charset=utf-8')
        ])

        yield self.body


class Main(Static):
    __slots__ = ()

    def __init__(
            self: WSGIApplication,
            import_name: str,
            static_url_path: str = None,
            static_folder: str | os.PathLike = None,
            static_encoding: str = None,
    ):
        root_path = os.path.dirname(sys.modules[import_name].__file__)

        super().__init__(root_path, static_url_path, static_folder, static_encoding)

    def __call__(self, environ: WSGIEnvironment, start_response: StartResponse) -> Iterable[bytes]:
        if file := self.file(environ):
            return self.file_wrapper(file, environ, start_response)

        return Routing(environ)(start_response)
