FROM tiangolo/uwsgi-nginx-flask:python3.6

RUN pip install --upgrade pip
RUN pip install flask flask-cors celery==4.2.0 redis==3.2.0 netcdf4 xarray matplotlib scipy seaborn dask statsmodels pandas toolz

COPY ./app /app
WORKDIR /app/

ENV STATIC_PATH /app/static
ENV STATIC_INDEX 1
