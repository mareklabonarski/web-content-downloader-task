FROM python:3.8

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN mkdir app

COPY requirements.txt app/requirements.txt
RUN pip install -r app/requirements.txt

COPY . app

WORKDIR /
