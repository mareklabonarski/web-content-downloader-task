from mongoengine import connect

from app.celery_tasks import *  #  noqa


connect(db='semantive', host='db')
