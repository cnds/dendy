import jwt
import logging

from datetime import timedelta, datetime


def create_jwt(data, secret, algorithm='HS256', expire_day=7):
    """ set default algorithm and expire time"""
    expire_time = timedelta(days=expire_day)
    json_content = {
        'exp': datetime.utcnow() + expire_time,
        'body': data
    }
    token = jwt.encode(json_content, secret, algorithm)
    return token


def decode_jwt(token, secret, algorithm='HS256', verify_expiration=True):
    try:
        data_decrypted = jwt.decode(
            token, secret, algorithm, verify_expiration)
    except Exception as ex:
        if ex == jwt.ExpiredSignature:
            logging.error('jwt expired signature error: %s' % ex)
        elif ex == jwt.DecodeError:
            logging.error('jwt decode error: %s' % ex)
        else:
            logging.error('unknown error: %s' % ex)
        return False, None
    else:
        return True, data_decrypted
