from celery import Celery, Task
from celery.utils.log import get_task_logger

import os, os.path, shutil
from datetime import timedelta, datetime as dt
import sqlite3
import zipfile

from tamsat_alert import tamsat_alert as ta
from tamsat_alert.extract_data import extract_point_timeseries
from config import config
import util
import database as db


log = get_task_logger(__name__)


# Setup the celery app
celery_app = Celery('tasks',
                    backend=config['Celery']['backend'],
                    broker=config['Celery']['broker'])

# This is necessary if we want the task to accept non-JSON compatible args (e.g. dates)
celery_app.conf.update(task_serializer='pickle',
                       accept_content=['json', 'pickle'])

# Run the cleanup every hour
celery_app.conf.beat_schedule = {
    'cleanup-files': {
        'task': 'tasks.cleanup_files',
        'schedule': 3600.0
    }
}

@celery_app.task()
def tamsat_alert_run(location, init_date, poi_start, poi_end, fc_start, fc_end, stat_type, tercile_weights, email, db_key, server_url):
    log.debug('Calling task')

    job_id = tamsat_alert_run.request.id

    # Update the database to indicate the job is running
    db.set_job_running(db_key, job_id)

    lon, lat = location

    # Setup an output directory in config['Tasks']['workdir']
    # This is based on the celery job ID, so should be unique
    output_path = os.path.join(config['Tasks']['workdir'], job_id)

    # Extract a DataFrame containing the data at the specified location
    data = extract_point_timeseries(config['Data']['path'], lon, lat)

    location_name = util.location_to_str(lon, lat)

    try:
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
        zipfile_name = util.get_zipfile_from_job_id(job_id)
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

        downloadLink = server_url + 'downloadResult?job_id='+job_id
        message = 'Your TAMSAT alert data is ready to download. '+ \
                  'You can retrieve it by visiting '+downloadLink+ \
                  '.  It will be available for '+ \
                  config['Tasks']['days_to_keep_completed']+ \
                  ' days, or '+config['Tasks']['hours_to_keep_downloaded']+ \
                  ' hours after you have downloaded it.'

        try:
            util.send_email(email, 'TAMSAT alert data ready', message, config['Email'])
        except Exception as e:
            log.error('Problem sending email', e)

        # Update the database to indicate the job is completed
        db.set_job_completed(db_key)
    except:
        db.set_error(job_id)



@celery_app.task
def cleanup_files():
    # Remove jobs from the database
    removed_jobs = db.remove_expired_jobs()

    # Now remove the associated files
    for job_id in removed_jobs:
        try:
            os.remove(util.get_zipfile_from_job_id(job_id))
        except Exception as e:
            log.error('Problem removing file with job id:'+job_id)

    return len(removed_jobs)
