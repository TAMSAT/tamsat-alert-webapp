import os, os.path, shutil
import hashlib
from celery import Celery, Task
from celery.utils.log import get_task_logger

from tamsat_alert import tamsat_alert as ta
from tamsat_alert.extract_data import extract_point_timeseries
from config import config

from time import time
from datetime import datetime as dt
import zipfile

ID_KEY = 'id'
COMPLETED_TIME_KEY = 'completed_time'

log = get_task_logger(__name__)

# Setup the working directory and create if necessary
workdir = config['Tasks']['workdir']
if(os.path.exists(workdir)):
    if(not os.path.isdir(workdir)):
        raise ValueError('The configured working directory (' +
                         workdir + ') exists, but it is not a directory')
else:
    os.mkdir(workdir)

# Setup the celery app
celery_app = Celery('tasks',
                    backend=config['Celery']['backend'],
                    broker=config['Celery']['broker'])

# This is necessary if we want the task to accept non-JSON compatible args (e.g. dates)
celery_app.conf.update(task_serializer='pickle',
                       accept_content=['json', 'pickle'])

from time import sleep

@celery_app.task()
def tamsat_alert_run(location, init_date, poi_start, poi_end, fc_start, fc_end, stat_type, tercile_weights, email):
    log.debug('Calling task')

    lon, lat = location

    # Setup an output directory in workdir
    # This is based on the celery job ID, so should be unique
    job_id = tamsat_alert_run.request.id
    output_path = os.path.join(workdir, job_id)

    sleep(30)
    open(get_zipfile_from_job_id(job_id), 'w').close()
    return {ID_KEY: job_id,
            COMPLETED_TIME_KEY: dt.now()}

    # Extract a DataFrame containing the data at the specified location
    data = extract_point_timeseries(config['Data']['path'], lon, lat)

    location_name = ''
    if(lat >= 0):
        location_name += '{0:.3f}°N'.format(lat)
    else:
        location_name += '{0:.3f}°S'.format(-lat)
    location_name += ', '
    if(lon >= 0):
        location_name += '{0:.3f}°E'.format(lon)
    else:
        location_name += '{0:.3f}°W'.format(-lon)

    # Run the job.  This will run the tamsat alert system, and write data to the
    # output directory
    ta.tamsat_alert(data,
                    init_date,
                    'rfe',
                    output_path,
                    poi_start.day, poi_start.month,
                    poi_end.day, poi_end.month,
                    fc_start.day, fc_start.month,
                    fc_end.day, fc_end.month,
                    tercile_weights,
                    int(config['Data']['climatology_start_year']),
                    int(config['Data']['climatology_end_year']),
                    int(config['Data']['period_of_interest_start_year']),
                    int(config['Data']['period_of_interest_end_year']),
                    location_name=location_name)

    # Now go into output_dir and create a zip file containing everything.
    zipfile_name = get_zipfile_from_job_id(job_id)
    zipf = zipfile.ZipFile(zipfile_name,
                           'w', zipfile.ZIP_DEFLATED)
    for root, dirs, files, in os.walk(output_path):
        for file in files:
            abs_file = os.path.join(root, file)
            zipf.write(abs_file,
                       arcname=os.path.relpath(abs_file, output_path))

    # Remove the output directory, since all of the output is now contained in the zip
    try:
        shutil.rmtree(output_path)
    except OSError as e:
        log.error('Problem removing working directory: '+output_path)

    # TODO send an email to the user, with link to a direct download.
    # TODO this will require an arg to this function with the server name

    return {ID_KEY: job_id,
            COMPLETED_TIME_KEY: dt.now()}

def get_zipfile_from_job_id(job_id):
    return os.path.join(workdir, job_id+'.zip')
