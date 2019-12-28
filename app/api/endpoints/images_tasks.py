from bson.errors import InvalidId
from flask_restplus import abort
from mongoengine import ValidationError
from werkzeug.utils import redirect

from app import models
from app.api import api
from app.api.endpoints import Task, TaskList
from app.models import StatusEnum


ns = api.namespace('images_tasks')


@ns.route('/')
class ImagesTaskList(TaskList):
    @property
    def model(self):
        return models.ImageTask

    @property
    def queryset(self):
        return super().queryset.exclude('images')

    @property
    def celery_task(self):
        from app import celery_tasks
        return celery_tasks.execute_images_task


@ns.route('/<string:tid>')
class ImagesTask(Task):
    @property
    def model(self):
        return models.ImageTask


@ns.route('/<string:tid>/images/')
class ImagesTaskImagesList(Task):
    @property
    def model(self):
        return models.Image

    @property
    def queryset(self):
        return super().queryset.exclude('tasks')

    def get(self, *args, **kwargs):
        tid = kwargs['tid']
        images = self.model.objects.filter(tasks=tid)
        return images.as_pymongo()


@ns.route('/<string:tid>/images/<string:iid>')
class ImagesTaskImage(Task):
    @property
    def model(self):
        return models.Image

    def get(self, *args, **kwargs):
        tid, iid = kwargs['tid'], kwargs['iid']
        try:
            image = self.model.objects.filter(pk=iid, tasks=tid, status=StatusEnum.SUCCESS).first_or_404()
        except (InvalidId, ValidationError):
            abort(404)
        else:
            return redirect(image['storage_url'])
