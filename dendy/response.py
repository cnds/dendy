from dendy.status import HTTPError, HTTP_CODES
from dendy.api import DEFAULT_CONTENT_TYPE


class Response(object):
    """ Represents an HTTP response to a client request.

    Attributes:
        status(str): HTTP status line(e.g., '200 OK').
        body(bytes): Byte string representing response content.
        headers(list): HTTP headers.
    """

    def init(self):
        self.status = HTTP_CODES[200]
        self.content_type = DEFAULT_CONTENT_TYPE
        self.headers = list()
        self.headers.append(('content-type', self.content_type))
        self.body = None

    def set_headers(self, headers):
        if isinstance(headers, dict):
            for k, v in headers.items():
                self.headers.append((str(k).lower(), v))
        else:
            raise HTTPError(500, TypeError('headers must be dict type'))

    def set_status(self, status_code, reason=None):
        self.status = HTTP_CODES.get(status_code, 'Unknown')
        self.body = reason
        return self.body
