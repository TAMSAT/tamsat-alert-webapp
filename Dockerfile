FROM tiangolo/uwsgi-nginx-flask:python3.6

RUN pip install --upgrade pip
RUN pip install flask flask-cors celery==4.2.0 redis==2.10.6

COPY ./app /app
WORKDIR /app/

ENV STATIC_PATH /app/static
ENV STATIC_INDEX 1
