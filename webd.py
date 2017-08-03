HTTP_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'HEAD']


class Request(object):
    def __init__(self, environ):
        self._environ = environ
        self.path = self._environ.get('PATH_INFO', '/').strip()

    @property
    def method(self):
        return self._environ.get('REQUEST_METHOD', 'GET').upper()

    @property
    def query_string(self):
        return self._environ.get('QUERY_STRING', '')

    @property
    def params(self):
        params = dict()
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
        return self._environ.get('Content-length', 0)

    @property
    def body(self):
        input_data = self._environ.get('wsgi.input')
        if input_data:
            return input_data.read()
        else:
            return dict()


class Response(object):
    def __init__(self):
        self.status = '200 OK'
        self.content_type = 'application/json; charset=utf-8'
        self.headers = list()
        self.headers.append(('content-type', self.content_type))
        self.body = None

    def set_headers(self, headers):
        if isinstance(headers, dict):
            for key, value in headers.items():
                self.headers.append((str(key).lower(), value))


class Application(object):
    def __init__(self, request=Request, response=Response):
        self._request = request
        self._response = response
        self.routes = dict()

    def __call__(self, environ, start_response):
        request = self._request(environ)
        response = self._response()
        headers = response.headers

        responder, params, method, uri_template = self._get_responder(request)
        responder(**params)

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
            except:
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
                responder = self.generate_responder(uri, method)
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
                responder = self.generate_responder(uri, method)

        return (responder, params, method, uri)

    def generate_responder(self, uri, method):
        responders = self.routes[uri]
        responder = None
        for method_allowed, responder_allowed in responders:
            if method_allowed == method:
                responder = responder_allowed
        if not responder:
            raise AttributeError('%s method is not allowed' % method)

        return responder

    def _get_body(self, response):
        body = response.body
        if body is not None:
            if not isinstance(body, bytes):
                body = body.encode('utf-8')
            return [body], len(body)

        return [], 0
