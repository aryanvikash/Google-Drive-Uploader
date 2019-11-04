# -*- coding: utf-8 -*-
import os
import json
import random
import binascii

import requests
from urlobject import URLObject
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from Crypto.Util import Counter

from mega.crypto import prepare_key, stringhash, encrypt_key, decrypt_key,\
    enc_attr, dec_attr, aes_cbc_encrypt_a32
from mega.utils import a32_to_str, str_to_a32, a32_to_base64, base64_to_a32,\
    mpi2int, base64urlencode, base64urldecode, get_chunks
from mega.exceptions import MegaRequestException, MegaIncorrectPasswordExcetion


class Mega(object):
    def __init__(self):
        self.seqno = random.randint(0, 0xFFFFFFFF)
        self.sid = None

    @classmethod
    def from_credentials(cls, email, password):
        inst = cls()
        inst.login_user(email, password)
        return inst

    @classmethod
    def from_ephemeral(cls):
        inst = cls()
        inst.login_ephemeral()
        return inst

    def api_req(self, data):
        params = {'id': self.seqno}
        self.seqno += 1
        if self.sid:
            params.update({'sid': self.sid})
        data = json.dumps([data])
        req = requests.post(
            'https://g.api.mega.co.nz/cs', params=params, data=data)
        json_data = req.json()
        if isinstance(json_data, int):
            raise MegaRequestException(json_data)
        return json_data[0]

    def login_user(self, email, password):
        password_aes = prepare_key(str_to_a32(password))
        uh = stringhash(email, password_aes)
        res = self.api_req({'a': 'us', 'user': email, 'uh': uh})
        self._login_common(res, password_aes)

    def login_ephemeral(self):
        random_master_key = [random.randint(0, 0xFFFFFFFF)] * 4
        random_password_key = [random.randint(0, 0xFFFFFFFF)] * 4
        random_session_self_challenge = [random.randint(0, 0xFFFFFFFF)] * 4
        user_handle = self.api_req({
            'a': 'up',
            'k': a32_to_base64(encrypt_key(random_master_key,
                                           random_password_key)),
            'ts': base64urlencode(a32_to_str(random_session_self_challenge) +
                                  a32_to_str(encrypt_key(
                                      random_session_self_challenge,
                                      random_master_key)))
        })
        res = self.api_req({'a': 'us', 'user': user_handle})
        self._login_common(res, random_password_key)

    def _login_common(self, res, password):
        if res in (-2, -9):
            raise MegaIncorrectPasswordExcetion("Incorrect e-mail and/or password.")
            
        enc_master_key = base64_to_a32(res['k'])
        self.master_key = decrypt_key(enc_master_key, password)
        if 'tsid' in res:
            tsid = base64urldecode(res['tsid'])
            key_encrypted = a32_to_str(
                encrypt_key(str_to_a32(tsid[:16]), self.master_key))
            if key_encrypted == tsid[-16:]:
                self.sid = res['tsid']
        elif 'csid' in res:
            enc_rsa_priv_key = base64_to_a32(res['privk'])
            rsa_priv_key = decrypt_key(enc_rsa_priv_key, self.master_key)

            privk = a32_to_str(rsa_priv_key)
            self.rsa_priv_key = [0, 0, 0, 0]

            for i in range(4):
                l = ((privk[0] * 256 + privk[1] + 7) // 8) + 2
                self.rsa_priv_key[i] = mpi2int(privk[:l])
                privk = privk[l:]

            enc_sid = mpi2int(base64urldecode(res['csid']))
            decrypter = RSA.construct(
                (self.rsa_priv_key[0] * self.rsa_priv_key[1],
                 0,
                 self.rsa_priv_key[2],
                 self.rsa_priv_key[0],
                 self.rsa_priv_key[1]))
            sid = '%x' % decrypter.key._decrypt(enc_sid)
            sid = binascii.unhexlify('0' + sid if len(sid) % 2 else sid)
            self.sid = base64urlencode(sid[:43])

    def get_files(self):
        files_data = self.api_req({'a': 'f', 'c': 1})
        for file in files_data['f']:
            if file['t'] in (0, 1):
                key = file['k'].split(':')[1]
                key = decrypt_key(base64_to_a32(key), self.master_key)
                # file
                if file['t'] == 0:
                    k = (key[0] ^ key[4],
                         key[1] ^ key[5],
                         key[2] ^ key[6],
                         key[3] ^ key[7])
                # directory
                else:
                    k = key
                attributes = base64urldecode(file['a'])
                attributes = dec_attr(attributes, k)
                file['a'] = attributes
                file['k'] = key
            # Root ("Cloud Drive")
            elif file['t'] == 2:
                self.root_id = file['h']
            # Inbox
            elif file['t'] == 3:
                self.inbox_id = file['h']
            # Trash Bin
            elif file['t'] == 4:
                self.trashbin_id = file['h']
        return files_data

    def download_from_url(self, url):
        url_object = URLObject(url)
        file_id, file_key = url_object.fragment[1:].split('!')
        
        #return the filename
        return self.download_file(file_id, file_key, public=True)

    def download_file(self, file_id, file_key, public=False, store_path=None):
        if public:
            file_key = base64_to_a32(file_key)
            file_data = self.api_req({'a': 'g', 'g': 1, 'p': file_id})
        else:
            file_data = self.api_req({'a': 'g', 'g': 1, 'n': file_id})

        k = (file_key[0] ^ file_key[4],
             file_key[1] ^ file_key[5],
             file_key[2] ^ file_key[6],
             file_key[3] ^ file_key[7])
        iv = file_key[4:6] + (0, 0)
        meta_mac = file_key[6:8]

        file_url = file_data['g']
        file_size = file_data['s']
        attributes = base64urldecode(file_data['at'])
        attributes = dec_attr(attributes, k)
        file_name = attributes['n']

        infile = requests.get(file_url, stream=True).raw
        if store_path:
            file_name = os.path.join(store_path, file_name)
        outfile = open(file_name, 'wb')

        counter = Counter.new(
            128, initial_value=((iv[0] << 32) + iv[1]) << 64)
        decryptor = AES.new(a32_to_str(k), AES.MODE_CTR, counter=counter)

        file_mac = (0, 0, 0, 0)
        for chunk_start, chunk_size in sorted(get_chunks(file_size).items()):
            chunk = infile.read(chunk_size)
            chunk = decryptor.decrypt(chunk)
            outfile.write(chunk)

            chunk_mac = [iv[0], iv[1], iv[0], iv[1]]
            for i in range(0, len(chunk), 16):
                block = chunk[i:i+16]
                if len(block) % 16:
                    block += b'\0' * (16 - (len(block) % 16))
                block = str_to_a32(block)
                chunk_mac = [
                    chunk_mac[0] ^ block[0],
                    chunk_mac[1] ^ block[1],
                    chunk_mac[2] ^ block[2],
                    chunk_mac[3] ^ block[3]]
                chunk_mac = aes_cbc_encrypt_a32(chunk_mac, k)

            file_mac = [
                file_mac[0] ^ chunk_mac[0],
                file_mac[1] ^ chunk_mac[1],
                file_mac[2] ^ chunk_mac[2],
                file_mac[3] ^ chunk_mac[3]]
            file_mac = aes_cbc_encrypt_a32(file_mac, k)

        outfile.close()

        # Integrity check
        if (file_mac[0] ^ file_mac[1], file_mac[2] ^ file_mac[3]) != meta_mac:
            raise ValueError('MAC mismatch')
        
        return file_name
    
    def get_public_url(self, file_id, file_key):
        public_handle = self.api_req({'a': 'l', 'n': file_id})
        decrypted_key = a32_to_base64(file_key)
        return 'http://mega.co.nz/#!%s!%s' % (public_handle, decrypted_key)

    def uploadfile(self, filename, dst=None):
        if not dst:
            root_id = getattr(self, 'root_id', None)
            if root_id == None:
                self.get_files()
            dst = self.root_id
        infile = open(filename, 'rb')
        size = os.path.getsize(filename)
        ul_url = self.api_req({'a': 'u', 's': size})['p']

        ul_key = [random.randint(0, 0xFFFFFFFF) for _ in range(6)]
        counter = Counter.new(
            128, initial_value=((ul_key[4] << 32) + ul_key[5]) << 64)
        encryptor = AES.new(
            a32_to_str(ul_key[:4]),
            AES.MODE_CTR,
            counter=counter)

        file_mac = [0, 0, 0, 0]
        for chunk_start, chunk_size in sorted(get_chunks(size).items()):
            chunk = infile.read(chunk_size)

            chunk_mac = [ul_key[4], ul_key[5], ul_key[4], ul_key[5]]
            for i in range(0, len(chunk), 16):
                block = chunk[i:i+16]
                if len(block) % 16:
                    block += b'\0' * (16 - len(block) % 16)
                block = str_to_a32(block)
                chunk_mac = [chunk_mac[0] ^ block[0],
                             chunk_mac[1] ^ block[1],
                             chunk_mac[2] ^ block[2],
                             chunk_mac[3] ^ block[3]]
                chunk_mac = aes_cbc_encrypt_a32(chunk_mac, ul_key[:4])

            file_mac = [file_mac[0] ^ chunk_mac[0],
                        file_mac[1] ^ chunk_mac[1],
                        file_mac[2] ^ chunk_mac[2],
                        file_mac[3] ^ chunk_mac[3]]
            file_mac = aes_cbc_encrypt_a32(file_mac, ul_key[:4])

            chunk = encryptor.encrypt(chunk)
            url = '%s/%s' % (ul_url, str(chunk_start))
            outfile = requests.post(url, data=chunk, stream=True).raw

            # assume utf-8 encoding. Maybe this entire section can be simplified
            # by not looking at the raw output
            # (http://docs.python-requests.org/en/master/user/advanced/#body-content-workflow)

            completion_handle = outfile.read().decode('utf-8')
        infile.close()

        meta_mac = (file_mac[0] ^ file_mac[1], file_mac[2] ^ file_mac[3])

        attributes = {'n': os.path.basename(filename)}
        enc_attributes = base64urlencode(enc_attr(attributes, ul_key[:4]))
        key = [ul_key[0] ^ ul_key[4],
               ul_key[1] ^ ul_key[5],
               ul_key[2] ^ meta_mac[0],
               ul_key[3] ^ meta_mac[1],
               ul_key[4], ul_key[5],
               meta_mac[0], meta_mac[1]]
        encrypted_key = a32_to_base64(encrypt_key(key, self.master_key))
        data = self.api_req({'a': 'p', 't': dst, 'n': [
            {'h': completion_handle,
             't': 0,
             'a': enc_attributes,
             'k': encrypted_key}]})
        return data
