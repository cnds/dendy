import hashlib
import binascii
from hashlib import pbkdf2_hmac


def create_md5_key(content):
    md5 = hashlib.md5()
    md5.update(content.encode('utf-8'))
    md5_content = md5.hexdigest()
    return md5_content


def create_hash_key(content, salt, iterations=10000):
    hashed_content = pbkdf2_hmac(
        'sha256', content.encode('utf-8'), salt.encode('utf-8'), iterations)
    hashed_content_hex = binascii.hexlify(hashed_content)
    return hashed_content_hex


def validate_hash_key(key, hashed_key, salt, iterations=10000):
    derived_key = create_hash_key(key, salt, iterations)
    if derived_key == hashed_key:
        return True

    return False
