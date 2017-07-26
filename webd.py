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


class Response(object):

    def __init__(self):
        self.status = 200
        self.content_type = 'application/json; charset=utf-8'
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
        start_response(response.status, headers)

        responder, params, method, uri_template = self._get_responder(request)
        responder(**params)

    def add_route(self, route, handler):
        """
        routes:
            {
                'GET': {
                    '/users/{user_id}': User
                },
                'POST': {
                    '/users': Users
                }
            }
        """
        if not isinstance(handler, type):
            raise TypeError('handler is not type string')

        if not route.startswith('/'):
            raise ValueError('route must start with "/"')

        if '//' in route:
            raise ValueError('route can not contain "//"')

        routes = dict()
        for method in HTTP_METHODS:
            try:
                responder = getattr(handler, method.lower())
            except:
                raise AttributeError('%s method is not allowed' % method)
            else:
                if callable(responder):
                    routes[method] = dict(route=responder)

        self.routes = routes

    def _get_responder(self, request):
        method = request.method
        route = request.path
        try:
            route_map = self.routes[method]
        except:
            raise AttributeError('%s method is not allowed' % method)

        uri_template = route_map.keys()[0]
        uri_splited = uri_template.split('/')  # '/users/{user_id}
        route_splited = route.split('/')       # '/users/abcd'
        params = dict()
        if len(uri_template) != len(route_splited):
            raise AttributeError('%s incorrect route')

        for index, item in enumerate(uri_splited):
            if item == route_splited[index]:
                continue
            else:
                if item.startswith('{') and item.endswith('}'):
                    params[item.rstrip('}').lstrip('{')] = route_splited['index']

        try:
            responder = route_map[route]
        except:
            raise AttributeError('%s method is not allowed' % method)

        return responder, params, method, uri_template
