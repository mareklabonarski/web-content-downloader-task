from flask import request
from flask_restplus import Resource, abort


class Task(Resource):
    @property
    def model(self):
        """ Return models class """
        raise NotImplementedError

    def get(self, *args, **kwargs):
        tid = kwargs['tid']
        return self.model.objects.get_or_404(pk=tid).to_mongo()


class TaskList(Resource):
    @property
    def model(self):
        """ Return models class """
        raise NotImplementedError
    
    @property
    def queryset(self):
        return self.model.objects.all()

    @property
    def celery_task(self):
        """ Return celery_tasks task function """
        raise NotImplementedError

    def get(self):
        return self.queryset.as_pymongo()

    def post(self):
        url = request.get_json().get('url')
        if not url:
            abort(400, message="Request need to contain 'url' parameter")

        # even if url is not unique, we want to download content is it can vary over time
        task = self.model.objects.create(url=url)
        self.celery_task.delay(task.to_json())

        return task.to_mongo(), 201
