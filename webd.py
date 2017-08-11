import json

HTTP_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'HEAD']

HTTP_CODES = {
    100: '100 Continue',
    101: '101 Switching Protocols',
    200: '200 OK',
    201: '201 Created',
    202: '202 Accepted',
    203: '203 Non-Authoritative Information',
    204: '204 No Content',
    205: '205 Reset Content',
    206: '206 Partial Content',
    300: '300 Multiple Choices',
    301: '301 Moved Permanently',
    302: '302 Found',
    303: '303 See Other',
    304: '304 Not Modified',
    305: '305 Use Proxy',
    306: '306 Reserved',
    307: '307 Temporary Redirect',
    400: '400 Bad Request',
    401: '401 Unauthorized',
    402: '402 Payment Required',
    403: '403 Forbidden',
    404: '404 Not Found',
    405: '405 Method Not Allowed',
    406: '406 Not Acceptable',
    407: '407 Proxy Authentication Required',
    408: '408 Request Timeout',
    409: '409 Conflict',
    410: '410 Gone',
    411: '411 Length Required',
    412: '412 Precondition Failed',
    413: '413 Request Entity Too Large',
    414: '414 Request-Uri Too Long',
    415: '415 Unsupported Media Type',
    416: '416 Requested Range Not Satisfiable',
    417: '417 Expectation Failed',
    500: '500 Internal Server Error',
    501: '501 Not Implemented',
    502: '502 Bad Gateway',
    503: '503 Service Unavailable',
    504: '504 Gateway Timeout',
    505: '505 Http Version Not Supported',
}

DEFAULT_CONTENT_TYPE = 'application/json; charset=utf-8'


class Request(object):
    def init(self, environ):
        self._environ = environ
        self._body = None
        self._headers = dict()

    @property
    def headers(self):
        for k, v in self._environ.items():
            if k.startswith('HTTP_'):
                self._headers[k[5:].replace('_', '-')] = v
            else:
                self._headers[k] = v
        return self._headers

    @property
    def path(self):
        return self.headers.get('PATH_INFO', '/').strip()

    @property
    def method(self):
        return self.headers.get('REQUEST_METHOD', 'GET').upper()

    @property
    def query_string(self):
        return self.headers.get('QUERY_STRING', '')

    @property
    def params(self):
        """ type: dict """
        params = dict()
        if self.query_string:
            for field in self.query_string.split('&'):
                k, _, v = field.partition('=')

            if k in params:
                old_value = params[k]
                if isinstance(old_value, list):
                    params[k] = old_value.append(v)
                else:
                    params[k] = [old_value, v]
            else:
                params[k] = v

        return params

    @property
    def content_length(self):
        return self.headers.get('CONTENT_LENGTH', 0)

    @property
    def body(self):
        """ type: dict """
        body_stream = self.headers.get('wsgi.input').read()
        if body_stream:
            try:
                self._body = json.loads(body_stream.decode('utf-8'))
            except json.JSONDecodeError as ex:
                raise Exception(ex)
        else:
            self._body = dict()
        return self._body

    @property
    def token(self):
        """ return json web token """
        prefix = 'Bearer'
        auth_header = self.headers.get('AUTHORIZATION')
        if auth_header is not None:
            return auth_header.partition(prefix)[-1].strip()

        return auth_header


class Response(object):
    def init(self):
        self.status = '200 OK'
        self.content_type = DEFAULT_CONTENT_TYPE
        self.headers = list()
        self.headers.append(('content-type', self.content_type))
        self.body = None

    def set_headers(self, headers):
        if isinstance(headers, dict):
            for key, value in headers.items():
                self.headers.append((str(key).lower(), value))

    def set_status(self, status_code, reason=None):
        self.status = HTTP_CODES.get(status_code, 'Unknown')
        self.body = reason
        return self.body


class Application(object):
    def __init__(self, request=Request, response=Response):
        self.routes = dict()

    def __call__(self, environ, start_response):
        request.init(environ)
        response.init()
        headers = response.headers

        responder, params, method, uri_template = self._get_responder(request)
        if responder is None:
            if method == 'HEAD':
                response.body = ''
            elif method == 'OPTIONS':
                response.body = ''
                allowed_methods = ', '.join(HTTP_METHODS)
                response.headers.append(('Allow', allowed_methods))
            else:
                response.status = HTTP_CODES[405]
        else:
            output = responder(**params)
            response.body = json.dumps(output)

        body, length = self._get_body(response)
        if length is not None:
            response.headers.append(('content-length', str(length)))

        start_response(response.status, headers)
        return body

    def add_route(self, route, resource):
        """
        routes: {
            '/users': [(GET, <bound method>), (POST, <bound method>)],
            '/users/{user_id}', [(PUT, <bound method>)]
        }

        resource: the instance of class that containing responder
        """

        if not isinstance(route, str):
            raise TypeError('route is not type string')

        if not route.startswith('/'):
            raise ValueError('route must start with "/"')

        if '//' in route:
            raise ValueError('route can not contain "//"')

        responders = list()
        for method in HTTP_METHODS:
            try:
                responder = getattr(resource, method.lower())
            except AttributeError:
                pass
            else:
                if callable(responder):
                    responders.append((method, responder))
                    self.routes.update({route: responders})

    def _get_responder(self, request):
        method = request.method
        route = request.path

        uri_templates = self.routes.keys()
        uri_part = [
            uri.lstrip('/').rstrip('/').split('/') for uri in uri_templates
        ]
        route_part = route.lstrip('/').rstrip('/').split('/')
        params = dict()
        for uri in uri_templates:
            uri_part = uri.lstrip('/').split('/')
            if len(uri_part) != len(route_part):
                continue

            if uri_part == route_part:
                responder = self._generate_responder(uri, method)
                break

            for index, item in enumerate(uri_part):
                if item == route_part[index]:
                    continue
                else:
                    if item.startswith('{') and item.endswith('}'):
                        params[item.rstrip('}').lstrip('{')] = route_part[
                            index]
                    else:
                        break
                responder = self._generate_responder(uri, method)

        return (responder, params, method, uri)

    def _generate_responder(self, uri, method):
        responders = self.routes[uri]
        responder = None
        for method_allowed, responder_allowed in responders:
            if method_allowed == method:
                responder = responder_allowed
        return responder

    def _get_body(self, response):
        body = response.body
        if body is not None:
            if not isinstance(body, bytes):
                body = body.encode('utf-8')
            return [body], len(body)

        return list(), 0


class HTTPStatus(Exception):
    def __init__(self, status, body=None, headers=None):
        self.status = status
        self.body = body
        self.headers = headers


request = Request()
response = Response()
