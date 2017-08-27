# Dendy

### Micro python web framework for creating REST API.

### Hello World

``` python
from webd import request, response, Api
from gevent.pywsgi import WSGIServer


class HelloWorld(object):

    def get(self, name):
        return 'Hello %s!' % name

    def post(self, name):
        result = response.set_status(
            400,
            reason='body content is {0}, name is {1}'.format(request.body,
                                                             name))
        return result

app = Api()
app.add_route('/{name}', HelloWorld())


if __name__ == '__main__':
    WSGIServer(('', 8000), app).serve_forever()
```
