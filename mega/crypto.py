# -*- coding: utf-8 -*-
import json

from Crypto.Cipher import AES

from mega.utils import a32_to_str, str_to_a32, a32_to_base64


def aes_cbc_encrypt(data, key):
    encryptor = AES.new(key, AES.MODE_CBC, '\0' * 16)
    return encryptor.encrypt(data)


def aes_cbc_decrypt(data, key):
    decryptor = AES.new(key, AES.MODE_CBC, '\0' * 16)
    return decryptor.decrypt(data)


def aes_cbc_encrypt_a32(data, key):
    return str_to_a32(aes_cbc_encrypt(a32_to_str(data), a32_to_str(key)))


def aes_cbc_decrypt_a32(data, key):
    return str_to_a32(aes_cbc_decrypt(a32_to_str(data), a32_to_str(key)))


def stringhash(s, aeskey):
    s32 = str_to_a32(s)
    h32 = [0, 0, 0, 0]
    for i in range(len(s32)):
        h32[i % 4] ^= s32[i]
    for _ in range(0x4000):
        h32 = aes_cbc_encrypt_a32(h32, aeskey)
    return a32_to_base64((h32[0], h32[2]))


def prepare_key(a):
    pkey = [0x93C467E3, 0x7DB0C7A4, 0xD1BE3F81, 0x0152CB56]
    for _ in range(0x10000):
        for j in range(0, len(a), 4):
            key = [0, 0, 0, 0]
            for i in range(4):
                if i + j < len(a):
                    key[i] = a[i + j]
            pkey = aes_cbc_encrypt_a32(pkey, key)
    return pkey


def encrypt_key(a, key):
    return sum(
        (aes_cbc_encrypt_a32(a[i:i+4], key)
            for i in range(0, len(a), 4)), ())


def decrypt_key(a, key):
    return sum(
        (aes_cbc_decrypt_a32(a[i:i+4], key)
            for i in range(0, len(a), 4)), ())


def enc_attr(attr, key):
    attr = 'MEGA' + json.dumps(attr)
    if len(attr) % 16:
        attr += '\0' * (16 - len(attr) % 16)
    return aes_cbc_encrypt(attr, a32_to_str(key))


def dec_attr(attr, key):
    attr = aes_cbc_decrypt(attr, a32_to_str(key)).decode('utf-8').rstrip('\0')
    return json.loads(attr[4:])
