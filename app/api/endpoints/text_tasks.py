from flask_restplus import abort

from app import models
from app.api import api
from app.api.endpoints import TaskList, Task


ns = api.namespace('text_tasks')


@ns.route('/')
class TextTaskList(TaskList):
    @property
    def model(self):
        return models.TextTask

    @property
    def celery_task(self):
        from app import celery_tasks
        return celery_tasks.execute_text_task


@ns.route('/<string:tid>')
class TextTask(Task):
    @property
    def model(self):
        return models.TextTask


@ns.route('/<string:tid>/text')
class TextTaskText(TextTask):
    @property
    def model(self):
        return models.TextTask

    def get(self, *args, **kwargs):
        text = super().get(*args, **kwargs).get('text')
        if text is None:
            abort(404)
        return {'text': text}
