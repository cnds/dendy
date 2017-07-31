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
        self.status = 200
        self.content_type = 'application/json; charset=utf-8'
        self.headers = dict()
        self.headers['content-type'] = self.content_type

    def set_headers(self, headers):
        if isinstance(headers, dict):
            for key, value in headers.items():
                self.headers[str(key).lower()] = value


class Application(object):

    def __init__(self, request=Request, response=Response):
        self._request = request
        self._response = response

    def __call__(self, environ, start_response):
        request = self._request(environ)
        response = self._response()
        headers = response.headers

        responder, params, method, uri_template = self._get_responder(request)
        responder(**params)

        start_response(response.status, headers)

    def add_route(self, route, handler):
        """
        routes: {
            '/users': [(GET, <bound method>), (POST, <bound method>)],
            '/users/{user_id}', [(PUT, <bound method>)]
        }
        """

        if not isinstance(handler, type):
            raise TypeError('handler is not type string')

        if not route.startswith('/'):
            raise ValueError('route must start with "/"')

        if '//' in route:
            raise ValueError('route can not contain "//"')

        routes = dict()
        method_and_responder = list()
        for method in HTTP_METHODS:
            try:
                responder = getattr(handler, method.lower())
            except:
                pass
            else:
                if callable(responder):
                    method_and_responder.append((method, responder))
                    routes.update({route: method_and_responder})

        self.routes = routes

    def _get_responder(self, request):
        # pending change ref add_route function
        method = request.method
        route = request.path
        try:
            route_map = self.routes[method]
        except:
            raise AttributeError('%s method is not allowed' % method)

        uri_template = route_map.keys()[0]
        uri_part = uri_template.split('/')  # '/users/{user_id}
        route_part = route.split('/')       # '/users/abcd'
        params = dict()
        if len(uri_part) != len(route_part):
            raise AttributeError('%s incorrect route')

        for index, item in enumerate(uri_part):
            if item == route_part[index]:
                continue
            else:
                if item.startswith('{') and item.endswith('}'):
                    params[item.rstrip('}').lstrip('{')] = route_part['index']

        try:
            responder = route_map[route]
        except:
            raise AttributeError('%s method is not allowed' % method)

        return responder, params, method, uri_template
