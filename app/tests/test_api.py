import pytest

from app import models
from app.tests.conftest import load_fixture_file
from app.utils import mongo_dumps_loads


@pytest.mark.parametrize('model, exclude, endpoint, fixture_file', [
    (models.ImageTask, ['images'], 'images_tasks', 'ImageTask__01.json'),
    (models.TextTask, [], 'text_tasks', 'TextTask__01.json'),
])
def test_api_get_task(client, model, exclude, endpoint, fixture_file, clean_db):
    load_fixture_file(fixture_file)

    tasks = model.objects.exclude(*exclude).all()

    response = client.get(f'/api/{endpoint}/invalid_id')

    assert response.status_code == 404

    for task in tasks:
        response = client.get(f"/api/{endpoint}/{task.pk}")

        assert response.status_code == 200
        assert response.json == mongo_dumps_loads(task)

    response = client.get(f'/api/{endpoint}/')

    assert response.status_code == 200
    assert response.json == mongo_dumps_loads(tasks)


@pytest.mark.parametrize('mock, model, endpoint, fixture_file', [
    ('mock_execute_images_task', models.ImageTask, 'images_tasks', 'ImageTask__01.json'),
    ('mock_execute_text_task', models.TextTask, 'text_tasks', 'TextTask__01.json'),
])
def test_api_post_images_task(
        client, clean_db, mock_execute_text_task, mock_execute_images_task, mock, model, endpoint, fixture_file):

    load_fixture_file(fixture_file)
    mock = {
        'mock_execute_images_task': mock_execute_images_task,
        'mock_execute_text_task': mock_execute_text_task,
    }[mock]

    url = 'http://www.google.pl'
    initial_no_tasks = model.objects.count()

    response = client.post(f'/api/{endpoint}/', json={'wrong_param': url})

    assert response.status_code == 400
    assert response.json['message'] == "Request need to contain 'url' parameter"
    assert not mock.delay.called
    assert model.objects.count() == initial_no_tasks

    response = client.post(f'/api/{endpoint}/', json={'url': url})

    assert response.status_code == 201
    assert response.json['url'] == url
    assert response.json['status'] == 'waiting'
    assert mock.delay.called
    assert model.objects.count() == initial_no_tasks + 1


def test_api_get_text(client, clean_db):
    load_fixture_file('TextTask__01.json')
    tasks = models.TextTask.objects.all()

    response = client.get('/api/text_tasks/invalid_id/text')
    assert response.status_code == 404

    response = client.get(f'/api/text_tasks/{tasks[0].pk}/text')
    assert response.status_code == 404

    response = client.get(f'/api/text_tasks/{tasks[1].pk}/text')
    assert response.status_code == 200
    assert response.json['text'] == tasks[1]['text']


def test_api_get_images(client, clean_db):
    load_fixture_file('ImageTask__01.json')
    load_fixture_file('Image__01.json')

    images = models.Image.objects.all()
    image_tasks = models.ImageTask.objects.all()
    image_tasks[0].update(images=images)
    images.update(tasks=[image_tasks[0]])

    response = client.get('/api/images_tasks/invalid_id/images/invalid_id')
    assert response.status_code == 404

    response = client.get(f'/api/images_tasks/{image_tasks[0].pk}/images/')
    assert response.status_code == 200

    response = client.get(f"/api/images_tasks/{image_tasks[0].pk}/images/{images[0].pk}")
    assert response.status_code == 404

    response = client.get(f"/api/images_tasks/{image_tasks[0].pk}/images/{images[2].pk}")
    assert response.status_code == 302
    assert images[2]['storage_url'] in response.location

    response = client.get(f"/api/images_tasks/{image_tasks[1].pk}/images/{images[0].pk}")
    assert response.status_code == 404
