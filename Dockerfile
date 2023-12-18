# syntax=docker/dockerfile:1
FROM python:3.8.10

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /code
RUN python --version
RUN pip install --upgrade pip
COPY requirements.txt /code/
RUN pip install -r requirements.txt

COPY . /code/

RUN ["chmod", "+x", "docker-entrypoint.sh"]
ENTRYPOINT ["sh", "docker-entrypoint.sh"]
CMD "python manage.py runserver 0.0.0.0:8000"
