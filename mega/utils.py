# -*- coding: utf-8 -*-
import base64
import struct
import binascii

from Crypto.Cipher import AES


def a32_to_str(a):
    return struct.pack('>%dI' % len(a), *a)


def aes_cbc_encrypt(data, key):
    encryptor = AES.new(key, AES.MODE_CBC, '\0' * 16)
    return encryptor.encrypt(data)


def aes_cbc_encrypt_a32(data, key):
    return str_to_a32(aes_cbc_encrypt(a32_to_str(data), a32_to_str(key)))


def str_to_a32(b):
    if len(b) % 4:  # Add padding, we need a string with a length multiple of 4
        b += '\0' * (4 - len(b) % 4)
    # For python3, we actually need bytes instead of a string.
    # This is a quick hack: a better solution would be to make sure
    # this function is only called with bytes as input
    if type(b) == str:
        b = bytes(b, 'utf-8') # utf-8 is an assumption here
    fmt = '>%dI' % (len(b) / 4)
    return struct.unpack(fmt, b)

def mpi2int(s):
    return int(binascii.hexlify(s[2:]), 16)


def aes_cbc_decrypt(data, key):
    decryptor = AES.new(key, AES.MODE_CBC, '\0' * 16)
    return decryptor.decrypt(data)


def aes_cbc_decrypt_a32(data, key):
    return str_to_a32(aes_cbc_decrypt(a32_to_str(data), a32_to_str(key)))


def base64urldecode(data):
    data += '=='[(2 - len(data) * 3) % 4:]
    for search, replace in (('-', '+'), ('_', '/'), (',', '')):
        data = data.replace(search, replace)
    return base64.b64decode(data)


def base64_to_a32(s):
    return str_to_a32(base64urldecode(s))


def base64urlencode(data):
    # add utf-8 encoding. likely there's a better method than b64encode
    # to get a string directly, as this looks like the point of base64 encoding
    data = base64.b64encode(data).decode('utf-8')
    for search, replace in (('+', '-'), ('/', '_'), ('=', '')):
        data = data.replace(search, replace)
    return data


def a32_to_base64(a):
    return base64urlencode(a32_to_str(a))


def get_chunks(size):
    chunks = {}
    p = pp = 0
    i = 1

    while i <= 8 and p < size - i * 0x20000:
        chunks[p] = i * 0x20000
        pp = p
        p += chunks[p]
        i += 1

    while p < size:
        chunks[p] = 0x100000
        pp = p
        p += chunks[p]

    chunks[pp] = size - pp
    if not chunks[pp]:
        del chunks[pp]

    return chunks
