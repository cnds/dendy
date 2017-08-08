import json

HTTP_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'HEAD']

HTTP_CODES = {
    100: 'CONTINUE',
    101: 'SWITCHING PROTOCOLS',
    200: 'OK',
    201: 'CREATED',
    202: 'ACCEPTED',
    203: 'NON-AUTHORITATIVE INFORMATION',
    204: 'NO CONTENT',
    205: 'RESET CONTENT',
    206: 'PARTIAL CONTENT',
    300: 'MULTIPLE CHOICES',
    301: 'MOVED PERMANENTLY',
    302: 'FOUND',
    303: 'SEE OTHER',
    304: 'NOT MODIFIED',
    305: 'USE PROXY',
    306: 'RESERVED',
    307: 'TEMPORARY REDIRECT',
    400: 'BAD REQUEST',
    401: 'UNAUTHORIZED',
    402: 'PAYMENT REQUIRED',
    403: 'FORBIDDEN',
    404: 'NOT FOUND',
    405: 'METHOD NOT ALLOWED',
    406: 'NOT ACCEPTABLE',
    407: 'PROXY AUTHENTICATION REQUIRED',
    408: 'REQUEST TIMEOUT',
    409: 'CONFLICT',
    410: 'GONE',
    411: 'LENGTH REQUIRED',
    412: 'PRECONDITION FAILED',
    413: 'REQUEST ENTITY TOO LARGE',
    414: 'REQUEST-URI TOO LONG',
    415: 'UNSUPPORTED MEDIA TYPE',
    416: 'REQUESTED RANGE NOT SATISFIABLE',
    417: 'EXPECTATION FAILED',
    500: 'INTERNAL SERVER ERROR',
    501: 'NOT IMPLEMENTED',
    502: 'BAD GATEWAY',
    503: 'SERVICE UNAVAILABLE',
    504: 'GATEWAY TIMEOUT',
    505: 'HTTP VERSION NOT SUPPORTED',
}


class Request(object):
    def init(self, environ):
        self._environ = environ
        self.path = self._environ.get('PATH_INFO', '/').strip()
        self._body = None

    @property
    def method(self):
        return self._environ.get('REQUEST_METHOD', 'GET').upper()

    @property
    def query_string(self):
        return self._environ.get('QUERY_STRING', None)

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
        return self._environ.get('CONTENT_LENGTH', 0)

    @property
    def body(self):
        """ type: dict """
        body_stream = self._environ.get('wsgi.input').read()
        if body_stream:
            try:
                self._body = json.loads(body_stream.decode('utf-8'))
            except json.JSONDecodeError as ex:
                raise Exception(ex)
        else:
            self._body = dict()
        return self._body


class Response(object):
    def init(self):
        self.status = '200 OK'
        self.content_type = 'application/json; charset=utf-8'
        self.headers = list()
        self.headers.append(('content-type', self.content_type))
        self.body = None

    def set_headers(self, headers):
        if isinstance(headers, dict):
            for key, value in headers.items():
                self.headers.append((str(key).lower(), value))

    def set_status(self, status_code, reason=None):
        self.status = ' '.join((str(status_code), HTTP_CODES.get(status_code, 'Unknown')))
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
        if method == 'HEAD':
            response.body = ''
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
