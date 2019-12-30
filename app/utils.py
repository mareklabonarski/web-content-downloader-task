import asyncio
import hashlib
import os
from functools import wraps

from bs4 import BeautifulSoup
from bson import ObjectId
from flask import json
from flask_mongoengine import BaseQuerySet
from flask_mongoengine.json import MongoEngineJSONEncoder
from uri import URI


class ParsingException(Exception):
    pass


def get_media_path():
    media_path = os.getenv('MEDIA_PATH')
    os.makedirs(media_path, exist_ok=True)
    return media_path


def get_text_from_html(html):
    try:
        soup = BeautifulSoup(html, 'html.parser')

        # kill all script and style elements (from stack overflow)
        for tag in soup(["script", "style"]):
            tag.decompose()  # rip it out
        return '\n'.join(line for line in soup.get_text().splitlines() if line)
    except (AssertionError, AttributeError, LookupError, TypeError, ValueError) as e:
        raise ParsingException from e


def get_images_from_html(html):
    try:
        soup = BeautifulSoup(html, 'html.parser')
        return [{'src': img['src'], 'name': img.get('alt')} for img in soup.find_all('img') if img.get('src')]
    except (AssertionError, AttributeError, LookupError, TypeError, ValueError) as e:
        raise ParsingException from e


def get_storage_path_and_url(src_url):
    # generate name unique per src_url, to prevent saving image twice -
    # FileExistsError is handled properly later on

    ext = os.path.splitext(src_url)[-1]
    storage_name = f"{hashlib.md5(src_url.encode()).hexdigest()}{ext}"
    storage_path = os.path.join(get_media_path(), storage_name)
    storage_url = f'/media/{storage_name}'
    return storage_path, storage_url


def write_to_storage(storage_path, content):
    with open(storage_path, mode='xb') as f:
        f.write(content)


def run_with_asyncio(async_func):
    @wraps(async_func)
    def inner(*args, **kwargs):
        return asyncio.get_event_loop().run_until_complete(async_func(*args, **kwargs))
    return inner


def get_url_from_src(src, task_url):
    base = URI(task_url)
    if src.startswith('//'):
        return str(base // src)
    return str(base / src)


class MongoEngineObjectIdJSONEncoder(MongoEngineJSONEncoder):
    """
    A JSONEncoder which provides serialization of MongoEngine
    documents and queryset objects.
    """

    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return MongoEngineJSONEncoder.default(self, obj)


def mongo_dumps(obj):
    as_mongo = obj.as_pymongo() if isinstance(obj, BaseQuerySet) else obj.to_mongo()
    return json.dumps(as_mongo, cls=MongoEngineObjectIdJSONEncoder)


def mongo_dumps_loads(obj):
    return json.loads(mongo_dumps(obj))

