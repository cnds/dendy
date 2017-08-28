from functools import wraps


def before(action):
    def _before(responder):
        @wraps(responder)
        def do_before(*args, **kwargs):
            action(*args, **kwargs)
            output = responder(*args, **kwargs)
            return output
        return do_before
    return _before


def after(action):
    def _after(responder):
        @wraps(responder)
        def do_after(*args, **kwargs):
            output = responder(*args, **kwargs)
            action(*args, **kwargs)
            return output
        return do_after
    return _after
