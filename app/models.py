import asyncio
import logging
from enum import Enum

import aiohttp
from app.fields import StringEnumField
from flask_mongoengine import Document
from mongoengine import DoesNotExist
from mongoengine.fields import *
import datetime

from app import utils
from app.utils import ParsingException, get_url_from_src

FORMAT = '%(asctime)-15s %(levelname)-10s %(message)s'
logging.basicConfig(level=logging.INFO, format=FORMAT)


class StatusEnum(Enum):
    WAITING = 'waiting'
    IN_PROGRESS = 'in progress'
    ERROR = 'error'
    SUCCESS = 'success'


class TaskException(Exception):
    pass


class Task(Document):
    url = URLField(required=True)
    status = StringEnumField(enum=StatusEnum, required=True, default=StatusEnum.WAITING)
    date_created = DateTimeField(default=datetime.datetime.utcnow)

    meta = {'allow_inheritance': True, 'abstract': True}

    async def get_html(self, session: aiohttp.ClientSession):
        try:
            response = await session.get(self.url)
            response.raise_for_status()
            return await response.text()
        except (aiohttp.ClientError, UnicodeError):
            logging.exception(f"Exception occurred when opening {self.url}")
            self.update(status=StatusEnum.ERROR)
            raise

    async def execute(self):
        raise NotImplementedError


class ImageTask(Task):
    images = ListField(ReferenceField('Image'))

    async def get_images(self, session):
        html = await self.get_html(session)
        try:
            html_images = utils.get_images_from_html(html)
        except ParsingException:
            self.update(status=StatusEnum.ERROR)
            raise

        for html_image in html_images:
            html_image['src'] = get_url_from_src(html_image['src'], self.url)
            try:
                image = Image.objects.get(src=html_image['src'])
            except DoesNotExist:
                image = Image.objects.create(**html_image)

            # if we had downloaded the image before or it is in progress by other task, still attach it to this task
            # we will skip download later on
            image.update(push__tasks=self.id)
            self.update(push__images=image.id)

    async def download_images(self, session):
        self.reload()

        # ERROR - if an image download had not succeeded before - retry
        # SUCCESS - if image had been already downloaded - skip
        # IN PROGRESS - if image is being downloaded by other task,
        #       let the other task to manage its status - skip
        coros = [
            image.download_image(self, session) for image in self.images
            if image.status in [StatusEnum.WAITING, StatusEnum.ERROR]
        ]
        results = await asyncio.gather(*coros, return_exceptions=True)

        if any(isinstance(result, Exception) for result in results):
            self.update(status=StatusEnum.ERROR)
            raise TaskException(f'Could not download some of images')

        self.update(status=StatusEnum.SUCCESS)

    async def execute(self):
        self.update(status=StatusEnum.IN_PROGRESS)

        async with aiohttp.ClientSession() as session:
            await self.get_images(session)
            await self.download_images(session)


class TextTask(Task):
    text = StringField(required=False)

    async def get_text(self, session: aiohttp.ClientSession):
        html = await self.get_html(session)

        try:
            text = utils.get_text_from_html(html)
        except ParsingException:
            logging.exception(f"Could not parse {self.url}")
            self.update(status=StatusEnum.ERROR)
            raise

        self.update(text=text, status=StatusEnum.SUCCESS)

    async def execute(self):
        self.update(status=StatusEnum.IN_PROGRESS)

        async with aiohttp.ClientSession() as session:
            await self.get_text(session)


class Image(Document):
    src = URLField(required=True, unique=True)
    name = StringField(max_length=128, required=False)
    status = StringEnumField(enum=StatusEnum, required=True, default=StatusEnum.WAITING)
    storage_url = StringField(required=False, regex=r'\/media\/[a-z0-9\.\-\_]*')
    date_created = DateTimeField(default=datetime.datetime.utcnow)
    tasks = ListField(ReferenceField(ImageTask))

    async def download_image(self, task, session):
        self.update(status=StatusEnum.IN_PROGRESS)

        try:
            response = await session.get(self.src)
            response.raise_for_status()
            content = await response.read()
        except (aiohttp.ClientError, UnicodeError):
            logging.exception(f"Exception occurred during {self.src} download for task {task.id}")
            self.update(status=StatusEnum.ERROR)
            raise

        storage_path, storage_url = utils.get_storage_path_and_url(self.src)
        try:

            utils.write_to_storage(storage_path, content)
        except FileExistsError:
            pass
        except OSError:
            logging.exception(f"Cannot open file to save image")
            self.update(status=StatusEnum.ERROR)
            raise

        self.update(storage_url=storage_url, status=StatusEnum.SUCCESS)
