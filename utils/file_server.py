import hashlib
import json
import ntpath
import os
import random
import shutil
from functools import partial
from math import ceil
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter

from sacentral.settings import FILE_SERVER_SECRET, FILE_SERVER
from utils.log import logger

DEFAULT_TIMEOUT = 10  # seconds

CHUCK_SIZE = 1024 * 1024 * 5
PUT_SIZE = 1024 * 1024 * 5


class TimeoutHTTPAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        self.timeout = DEFAULT_TIMEOUT
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)


def md5_hash(data, block_size=65536):
    m = hashlib.md5()
    for item in iter(partial(data.read, block_size), b''):
        m.update(item)
    str_md5 = m.hexdigest()
    return str_md5


def upload_file(files, payload=None):
    if payload is None:
        payload = {}
    url = urljoin(random.choice(FILE_SERVER), 'upload')
    headers = {
        'Authorization': FILE_SERVER_SECRET
    }
    logger.info('upload_file request:{}'.format(payload))
    response = requests.request("POST", url, headers=headers, data=payload, files=files, timeout=15)
    response = json.loads(response.text.encode('utf8'))
    logger.info('upload file response:{}'.format(response))
    if response.get('code', 0) != '200':
        raise ValueError('file upload code error')
    if not response.get('result', None):
        raise ValueError('file upload data none')
    data = response.get('result')
    if not data['success']:
        raise Exception('file upload fail')


def init_part(payload=None):
    if payload is None:
        payload = {}
    url = urljoin(random.choice(FILE_SERVER), 'part/init')
    headers = {
        'Authorization': FILE_SERVER_SECRET
    }
    logger.info('init_part request:{}'.format(payload))
    response = requests.request("POST", url, headers=headers, data=payload, timeout=5)
    response = json.loads(response.text.encode('utf8'))
    logger.info('part init file response:{}'.format(response))
    if response.get('code', 0) != '200':
        raise ValueError('part init code error')
    if not response.get('result', None):
        raise ValueError('part init data none')
    upload_id = response.get('result')
    logger.info('part init requestId:{}'.format(upload_id))
    return upload_id


def part_put(files, payload=None):
    if payload is None:
        payload = {}
    url = urljoin(random.choice(FILE_SERVER), 'part')
    headers = {
        'Authorization': FILE_SERVER_SECRET
    }
    logger.info('part_put request:{}'.format(payload))

    http = requests.Session()

    # Mount it for both http and https usage
    adapter = TimeoutHTTPAdapter(timeout=30)
    http.mount("https://", adapter)
    http.mount("http://", adapter)
    response = http.post(url, data=payload, headers=headers, files=files)
    response = json.loads(response.text.encode('utf8'))
    logger.info('part file response:{}'.format(response))
    if response.get('code', 0) != '200':
        raise ValueError('part code error')
    if not response.get('result', None):
        raise ValueError('part data none')
    data = response.get('result')
    if not data['success']:
        raise Exception('part upload fail')
    return data


def part_complete(payload=None):
    if payload is None:
        payload = {}
    url = urljoin(random.choice(FILE_SERVER), 'part/complete')
    headers = {
        'Authorization': FILE_SERVER_SECRET
    }

    logger.info('part_complete request:{}'.format(payload))
    response = requests.request("POST", url, headers=headers, data=payload, timeout=5)
    response = json.loads(response.text.encode('utf8'))
    logger.info('part complete response:{}'.format(response))
    if response.get('code', 0) != '200':
        raise ValueError('part complete error')
    if not response.get('result', None):
        raise ValueError('part complete none')
    data = response.get('result')
    if not data['success']:
        raise Exception('part complete fail')


def preview(payload=None):
    if payload is None:
        payload = {}
    url = urljoin(random.choice(FILE_SERVER), 'preview')
    headers = {
        'Authorization': FILE_SERVER_SECRET
    }
    logger.info('preview request:{}'.format(payload))
    response = requests.request("POST", url, headers=headers, data=payload, timeout=5)
    response = json.loads(response.text.encode('utf8'))
    logger.info('preview response:{}'.format(response))
    if response.get('code', 0) != '200':
        raise ValueError('preview error')
    if not response.get('result', None):
        raise ValueError('preview none')
    data = response.get('result')
    if not data['success']:
        raise Exception('preview fail')

    return data['url']


def download(payload=None):
    if payload is None:
        payload = {}
    logger.info('download request:{}'.format(payload))
    url = urljoin(random.choice(FILE_SERVER), 'download')
    headers = {
        'Authorization': FILE_SERVER_SECRET
    }
    response = requests.request("POST", url, headers=headers, data=payload, timeout=5)
    response = json.loads(response.text.encode('utf8'))
    logger.info('download response:{}'.format(response))
    if response.get('code', 0) != '200':
        raise ValueError('download error')
    if not response.get('result', None):
        raise ValueError('download none')
    data = response.get('result')
    if not data['success']:
        raise Exception('download fail')

    return data['url']


def delete(payload=None):
    if payload is None:
        payload = {}
    url = urljoin(random.choice(FILE_SERVER), 'delete')
    headers = {
        'Authorization': FILE_SERVER_SECRET
    }

    logger.info('delete request:{}'.format(payload))
    response = requests.request("POST", url, headers=headers, data=payload, timeout=5)
    response = json.loads(response.text.encode('utf8'))
    logger.info('delete response:{}'.format(response))
    if response.get('code', 0) != '200':
        raise ValueError('delete error')
    if not response.get('result', None):
        raise ValueError('delete none')
    data = response.get('result')
    if not data['success']:
        raise Exception('delete fail')


def download_write_local(url, file_name):
    response_data_file = requests.get(url, stream=True)
    with open(file_name, 'wb') as f:
        for chunk in response_data_file.iter_content(chunk_size=1024 * 1024 * 10):
            if chunk:
                f.write(chunk)


def zipdir(output_filename, dir_name):
    shutil.make_archive(output_filename, 'zip', dir_name)
    return output_filename + '.zip'


def calculate_md5(filepath):
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def test(path):
    md5_l = hashlib.md5()
    with open(path, mode="rb") as f:
        by = f.read()

    md5_l.update(by)
    ret = md5_l.hexdigest()
    print(ret)

    md5 = str(ret).lower()
    print(md5)


def convert_to_posix(origin):
    import os
    import posixpath
    return origin.replace(os.sep, posixpath.sep)


def file_info(file_path):
    if not os.path.exists(file_path):
        raise AssertionError('file:{} does not exist.'.format(file_path))
    name = ntpath.basename(file_path)
    size = os.path.getsize(file_path)
    parts = ceil(size / CHUCK_SIZE)

    logger.info('name:{}, size:{}, parts:{}'.format(name, size, parts))
    return name, size, parts


def digest_hash(path, hash_type='md5', block_size=64 * 1024):
    """ Support md5(), sha1(), sha224(), sha256(), sha384(), sha512(), blake2b(), blake2s(),
    sha3_224, sha3_256, sha3_384, sha3_512, shake_128, and shake_256
    """
    with open(path, 'rb') as file:
        digest = hashlib.new(hash_type, b'')
        while True:
            data = file.read(block_size)
            if not data:
                break
            digest.update(data)
        return digest.hexdigest()


def upload(file_path, folder):
    name, size, parts = file_info(file_path)
    md5 = digest_hash(file_path)
    object_key = folder + '/' + md5 + '/' + name
    if size < PUT_SIZE:
        post_mini_file(file_path, object_key)
    else:
        payload = {'objectKey': object_key}
        upload_id = init_part(payload)
        from functools import partial
        part = 0
        etags = []
        with open(file_path, 'rb') as file:
            for chunk in iter(partial(file.read, CHUCK_SIZE), b''):
                part += 1
                payload = {
                    'objectKey': object_key,
                    'uploadId': upload_id,
                    'partNumber': part
                }
                files = [
                    ('file', chunk)
                ]
                result = part_put(files, payload)
                etags.append(result.get('etag'))
        payload = {
            'uploadId': upload_id,
            'objectKey': object_key,
            'size': parts,
            'md5': md5,
            'etags': ','.join(etags)

        }
        part_complete(payload)
    return name, size, parts, md5, object_key


def post_mini_file(file_path, object_key):
    payload = {'objectKey': object_key}
    with open(file_path, 'rb') as f:
        files = [
            ('file', f)
        ]
        upload_file(files, payload)


if __name__ == "__main__":
    file_path = '/home/ran/download/love-master.zip'
    upload(file_path, 'codezip')
