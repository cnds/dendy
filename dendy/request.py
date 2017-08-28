import json


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
        """
        convert query sting to dictionary
        """
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
        return self.headers.get('CONTENT_LENGTH', 0)

    @property
    def body(self):
        """
        get input body data
        type: dict
        """
        body_stream = self.headers.get('wsgi.input').read()
        if body_stream:
            try:
                self._body = json.loads(body_stream.decode('utf-8'))
            except json.JSONDecodeError as ex:
                raise HTTPError(500, ex)
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


request = Request()