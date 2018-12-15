import json

from dendy.request import req
from dendy.response import resp
from dendy.status import HTTPError, HTTP_CODES


HTTP_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'HEAD']


class API(object):
    """The main entry point into a Dendy app.

    Each API instance provides a callable WSGI interface and a routing engine.

    Keyword Arguments:
        middleware(list or object):

            class ExampleMiddleware(object):

                def process_before(self, req, resp):
                    '''
                    Process the request before routing it. 
                    '''

                def process_on(self, req, resp, params):
                    '''
                    Process the request and response after routing.
                    '''

                def process_after(self, req, resp, params):
                    '''
                    Post-process of the response.
                    '''


    """

    def __init__(self, middleware=None):
        self.routes = dict()
        self._middleware = self.prepare_middleware(middleware)

    def __call__(self, environ, start_response):
        req.init(environ)
        resp.init()
        headers = resp.headers
        after_stack = list()
        params = dict()

        try:
            for component in self._middleware:
                process_before, _, process_after = component
                if process_before is not None:
                    process_before(req, resp)

                if process_after is not None:
                    after_stack.append(process_after)

            responder, params, method = self._get_responder()
        except Exception as ex:
            raise HTTPError(500, ex)
        else:
            if responder is not None:
                for component in self._middleware:
                    _, process_on, _ = component
                    if process_on is not None:
                        process_on(req, resp, params)

                output = responder(**params)
                resp.body = json.dumps(output)
            else:
                if method == 'HEAD':
                    resp.body = ''
                elif method == 'OPTIONS':
                    allowed_methods = ', '.join(HTTP_METHODS)
                    resp.headers.append(('Allow', allowed_methods))
                else:
                    resp.status = HTTP_CODES[405]

        finally:
            for process_after in after_stack:
                process_after(req, resp, params)

        body, length = self._get_body()
        if length is not None:
            resp.headers.append(('content-length', str(length)))

        start_response(resp.status, headers)
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
            raise HTTPError(500, TypeError('route is not type string'))

        if not route.startswith('/'):
            raise HTTPError(500, ValueError('route must start with "/"'))

        if '//' in route:
            raise HTTPError(500, ValueError('route can not contain "//"'))

        responders = list()
        for method in HTTP_METHODS:
            try:
                responder = getattr(resource, method.lower())
            except AttributeError:
                pass
            else:
                if callable(responder):
                    responders.append((method, responder))

        if self.routes.get(route.rstrip('/')):
            raise HTTPError(500, 'conflict route exists: %s' % route)

        self.routes.update({route: responders})

    def _get_responder(self):
        method = req.method
        route = req.path
        responder = None
        params = dict()

        route_part = route.lstrip('/').rstrip('/').split('/')

        uri_templates = self.routes.keys()
        for uri in uri_templates:
            uri_part = uri.lstrip('/').rsplit('/')
            if len(uri_part) != len(route_part):
                continue

            if uri_part == route_part:
                responder = self._generate_responder(uri, method)

            else:
                for i, j in enumerate(uri_part):
                    if j.startswith('{') and j.endswith('}'):
                        params[j.rstrip('}').lstrip('{')] = route_part[i]
                        responder = self._generate_responder(uri, method)

        return responder, params, method

    def _generate_responder(self, uri, method):
        responders = self.routes[uri]
        responder = None
        for method_defined, responder_defined in responders:
            if method_defined == method:
                responder = responder_defined
        return responder

    @staticmethod
    def _get_body():
        body = resp.body
        if body is not None:
            if not isinstance(body, bytes):
                body = body.encode('utf-8')
            return [body], len(body)

        return list(), 0

    @staticmethod
    def prepare_middleware(middleware=None):
        prepared_middleware = list()

        if middleware is None:
            middleware = list()
        else:
            if not isinstance(middleware, list):
                middleware = [middleware]

        for component in middleware:
            process_before = getattr(component, 'process_before', None)
            process_on = getattr(component, 'process_on', None)
            process_after = getattr(component, 'process_after', None)

            if not (process_before or process_on or process_after):
                raise HTTPError(500,
                                TypeError('%s is not implemented' % component))

            prepared_middleware.append((process_before, process_on,
                                        process_after))

        return prepared_middleware
