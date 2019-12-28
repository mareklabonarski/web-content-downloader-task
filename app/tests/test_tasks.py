import aiohttp
import pytest

from app import models
from app.celery_tasks import execute_text_task, execute_images_task
from app.models import StatusEnum
from app.tests.conftest import load_fixture_file, get_image_dicts
from app.utils import run_with_asyncio, ParsingException


@pytest.mark.parametrize(
    'target, side_effect, side_effect_target, status',
    [
        ('session_object_mock', None, 'get', StatusEnum.SUCCESS),
        ('session_object_mock', aiohttp.ClientError, 'get', StatusEnum.ERROR),
        ('session_object_mock', UnicodeError, 'get.return_value.text', StatusEnum.ERROR),
        ('app.utils.get_text_from_html', ParsingException, '', StatusEnum.ERROR),
    ],
    ids=['successful', 'load page exception', 'page content decode error', 'parsing exception']
)
def test_execute_text_task(
        test_app, clean_db, session_object_mock, mock_session_ctx, set_side_effect, target,
        side_effect, side_effect_target, status):

    load_fixture_file('TextTask__01.json')
    task = models.TextTask.objects.first()

    text = """Testing — aiohttp 3.6.2 documentation
Testing¶
Testing aiohttp web servers¶
aiohttp provides plugin for pytest making writing web server tests
extremely easy, it also provides test framework agnostic
utilities for testing
with other frameworks such as unittest.
Before starting to write your tests, you may also be interested on
reading how to write testable
services that interact
with the loop.
For using pytest plugin please install pytest-aiohttp library:
$ pip install pytest-aiohttp"""

    set_side_effect(locals(), target, side_effect_target, side_effect)

    if side_effect:
        with pytest.raises(side_effect):
            execute_text_task(task.to_json())
    else:
        execute_text_task(task.to_json())
    task.reload()

    assert task.text == (text if not side_effect else None)
    assert task.status == status


@pytest.mark.parametrize(
    'target, side_effect, side_effect_target, status',
    [
        ('session_object_mock', None, 'get', StatusEnum.SUCCESS),
        ('session_object_mock', aiohttp.ClientError, 'get', StatusEnum.ERROR),
        ('session_object_mock', UnicodeError, 'get.return_value.text', StatusEnum.ERROR),
        ('app.utils.get_images_from_html', ParsingException, '', StatusEnum.ERROR),
    ],
    ids=['successful', 'load page exception', 'page content decode error', 'parsing exception']
)
def test_task_get_images(
        test_app, clean_db, mocker, session_object_mock,
        set_side_effect, target, side_effect, side_effect_target, status):

    load_fixture_file('ImageTask__01.json')
    task = models.ImageTask.objects.first()

    _html_images = get_image_dicts(exclude=('status', 'storage_url', 'tasks'))
    
    mocker.patch.object(models.utils, 'get_images_from_html', return_value=_html_images)
    set_side_effect(locals(), target, side_effect_target, side_effect)

    if side_effect:
        with pytest.raises(side_effect):
            run_with_asyncio(task.get_images)(session_object_mock)
    else:
        run_with_asyncio(task.get_images)(session_object_mock)
    task.reload()

    if side_effect:
        assert len(task.images) == 0
    else:
        assert len(task.images) == len(_html_images)
        assert set(img.src for img in task.images) == set(img['src'] for img in _html_images)


@pytest.mark.parametrize(
    'target, side_effect, side_effect_target, status',
    [
        ('session_object_mock', None, 'get', StatusEnum.SUCCESS),
        ('session_object_mock', aiohttp.ClientError, 'get', StatusEnum.ERROR),
        ('app.utils.write_to_storage', OSError, '', StatusEnum.ERROR),
        ('app.utils.write_to_storage', FileExistsError, '', StatusEnum.SUCCESS),
    ],
    ids=['successful', 'download failed', 'cannot open file to save image', 'image exists in storage']
)
def test_image_download_image(
        test_app, clean_db, mocker, session_object_mock, target, set_side_effect,
        side_effect, side_effect_target, status):

    load_fixture_file('ImageTask__01.json')
    load_fixture_file('Image__01.json')

    storage_url = '/media/file.png'
    mocker.patch.object(models.utils, 'write_to_storage')
    mocker.patch.object(models.utils, 'get_storage_path_and_url', return_value=('x', storage_url))
    set_side_effect(locals(), target, side_effect_target, side_effect)

    task = models.ImageTask.objects.first()
    image = models.Image.objects.first()
    
    raises = side_effect and side_effect is not FileExistsError

    if raises:
        with pytest.raises(side_effect):
            run_with_asyncio(image.download_image)(task, session_object_mock)
    else:
        run_with_asyncio(image.download_image)(task, session_object_mock)
    image.reload()
    
    assert image.status == status
    assert image.storage_url == (None if raises else storage_url)


@pytest.mark.parametrize(
    'target, side_effect, side_effect_target, task_status, image_status',
    [
        ('session_object_mock', None, 'get', StatusEnum.SUCCESS, StatusEnum.SUCCESS),
        ('session_object_mock', aiohttp.ClientError, 'get', StatusEnum.ERROR, StatusEnum.ERROR),
        ('app.utils.write_to_storage', OSError, '', StatusEnum.ERROR, StatusEnum.ERROR),
        ('app.utils.write_to_storage', FileExistsError, '', StatusEnum.SUCCESS, StatusEnum.SUCCESS),
    ],
    ids=['successful', 'download failed', 'cannot open file to save image', 'image exists in storage']
)
def test_task_download_images(
        test_app, clean_db, session_object_mock, mocker, set_side_effect,
        target, side_effect, side_effect_target, task_status, image_status):

    load_fixture_file('ImageTask__01.json')
    load_fixture_file('Image__01.json')
    task = models.ImageTask.objects.first()
    images = models.Image.objects.all()

    initial_statuses = {img.id: img.status for img in images}

    task.update(images=images)

    storage_url = '/media/file.png'
    mocker.patch.object(models.utils, 'write_to_storage')
    mocker.patch.object(models.utils, 'get_storage_path_and_url', return_value=('x', storage_url))
    set_side_effect(locals(), target, side_effect_target, side_effect)

    raises = side_effect and side_effect is not FileExistsError

    if raises:
        with pytest.raises(Exception):
            run_with_asyncio(task.download_images)(session_object_mock)
    else:
        run_with_asyncio(task.download_images)(session_object_mock)
    task.reload()

    assert task.status == task_status

    for img in task.images:
        assert img.status == \
            image_status if initial_statuses[img.id] in [StatusEnum.WAITING, StatusEnum.ERROR] \
            else initial_statuses[img.id]


@pytest.mark.parametrize(
    'target, side_effect, side_effect_target, task_status, image_status, no_img',
    [
        ('session_object_mock', None, 'get', StatusEnum.SUCCESS, StatusEnum.SUCCESS, 4),
        ('session_object_mock', aiohttp.ClientError, 'get', StatusEnum.ERROR, StatusEnum.ERROR, 0),
        ('session_object_mock', UnicodeError, 'get.return_value.text', StatusEnum.ERROR, StatusEnum.ERROR, 0),
        ('app.utils.get_images_from_html', ParsingException, '', StatusEnum.ERROR, StatusEnum.ERROR, 0),
        ('session_object_mock', UnicodeError, 'get.return_value.read', StatusEnum.ERROR, StatusEnum.ERROR, 4),
        ('app.utils.write_to_storage', OSError, '', StatusEnum.ERROR, StatusEnum.ERROR, 4),
        ('app.utils.write_to_storage', FileExistsError, '', StatusEnum.SUCCESS, StatusEnum.SUCCESS, 4),
    ],
    ids=[
        'successful',
        'load page exception',
        'page content decode error',
        'parsing exception',
        'image download failed',
        'cannot open file to save image',
        'image exists in storage'
    ]
)
def test_execute_images_task(
        test_app, clean_db, mock_session_ctx, session_object_mock, mocker, set_side_effect,
        target, side_effect, side_effect_target, task_status, image_status, no_img):

    load_fixture_file('ImageTask__01.json')
    tasks = models.ImageTask.objects.all()

    task = tasks[0]
    _html_images = get_image_dicts(exclude=('status', 'storage_url', 'tasks'))

    mocker.patch.object(models.utils, 'get_images_from_html', return_value=_html_images)
    mocker.patch.object(models.utils, 'write_to_storage')
    mocker.patch.object(models.utils, 'get_media_path', return_value='/media')
    set_side_effect(locals(), target, side_effect_target, side_effect)

    raises = side_effect and side_effect is not FileExistsError

    if raises:
        with pytest.raises((side_effect, models.TaskException)):
            execute_images_task(task.to_json())
    else:
        execute_images_task(task.to_json())
    task.reload()

    assert task.status == task_status
    assert len(task.images) == no_img
    for img in task.images:
        assert img.status == image_status
