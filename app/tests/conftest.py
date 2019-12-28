import json
import os
from functools import reduce

import asynctest
import pytest
from asynctest import CoroutineMock

from app import models
from app.app import create_app


FIXTURES_PATH = os.path.join(os.path.dirname(__file__), 'fixtures')


def html_response():
    with open(os.path.join(os.path.dirname(__file__), 'fixtures', 'index.html'), 'rb') as f:
        return f.read()


def get_image_dicts(exclude=None):
    exclude = exclude or []
    with open(os.path.join(FIXTURES_PATH, 'Image__01.json')) as f:
        fixture_images = json.load(f)

    return [{key: value for key, value in img.items() if key not in exclude} for img in fixture_images]


@pytest.fixture
def mock_execute_images_task(mocker):
    return mocker.patch('app.celery_tasks.execute_images_task')


@pytest.fixture
def mock_execute_text_task(mocker):
    return mocker.patch('app.celery_tasks.execute_text_task')


@pytest.fixture
def session_object_mock():
    mock_object = asynctest.MagicMock()
    mock_object.get = CoroutineMock()
    mock_object.get.return_value = CoroutineMock()
    mock_object.get.return_value.read = CoroutineMock()
    mock_object.get.return_value.read.return_value = b'ABCD'
    mock_object.get.return_value.text = CoroutineMock()
    mock_object.get.return_value.text.return_value = html_response()
    yield mock_object


@pytest.fixture
def session_context_mock(session_object_mock):
    mock_object = asynctest.MagicMock()
    mock_object.__aenter__.return_value = session_object_mock
    return mock_object


@pytest.fixture
def set_side_effect(mocker):
    def _set_side_effect(locals, obj_name_or_path, target, side_effect):
        if obj_name_or_path in locals:
            obj = locals[obj_name_or_path]
            return mocker.patch.object(reduce(getattr, [obj, *target.split('.')]), 'side_effect', side_effect)
        return mocker.patch(obj_name_or_path, side_effect=side_effect)
    return _set_side_effect


@pytest.fixture
def mock_session_ctx(session_context_mock, mocker):
    return mocker.patch('aiohttp.ClientSession', return_value=session_context_mock)


@pytest.fixture
def clean_db():
    _models = ['TextTask', 'ImageTask', 'Image']
    for model in _models:
        getattr(models, model).drop_collection()


@pytest.fixture
def test_app(mock_execute_images_task, mock_execute_text_task):
    app = create_app(testing=True)
    yield app


@pytest.fixture
def client(test_app):
    with test_app.test_client() as client:
        yield client


def load_fixture_file(filename):
    model = getattr(models, filename.split('__')[0])
    filepath = os.path.join(FIXTURES_PATH, filename)
    with open(filepath, 'r') as f:
        data = json.load(f)
    for d in data:
        model.objects.create(**d)
