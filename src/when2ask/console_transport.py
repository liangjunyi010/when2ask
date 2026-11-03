"""Small JSON-only HTTP transport shared by local and VPN execution workers."""
import http.client
import json
from urllib.parse import urlsplit


class WireError(RuntimeError):
    pass


def request(base, path, body=None, *, token=None, timeout=20):
    url = urlsplit(base)
    if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password or url.path not in ('', '/'):
        raise ValueError('Controller must be an http(s) origin')
    cls = http.client.HTTPSConnection if url.scheme == 'https' else http.client.HTTPConnection
    connection = cls(url.hostname, url.port, timeout=timeout)
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    try:
        connection.request('POST' if body is not None else 'GET', path,
                           json.dumps(body).encode() if body is not None else None, headers)
        response = connection.getresponse()
        data = json.loads(response.read())
        if response.status >= 400:
            raise WireError(data.get('error', f'HTTP {response.status}'))
        return data
    finally:
        connection.close()
