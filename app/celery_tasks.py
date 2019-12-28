from celery import Celery

from app.models import ImageTask, TextTask
from app.utils import run_with_asyncio


celery_app = Celery('celery_tasks', broker='amqp://broker')


@celery_app.task
def execute_images_task(json_task):
    task = ImageTask.from_json(json_task)
    task.reload()
    run_with_asyncio(task.execute)()


@celery_app.task
def execute_text_task(json_task):
    task = TextTask.from_json(json_task)
    task.reload()
    run_with_asyncio(task.execute)()
