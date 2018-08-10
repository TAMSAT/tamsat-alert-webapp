import configparser
import os
import logging
from tamsat_alert import tamsat_alert as ta
from datetime import datetime as dt
from celery import Celery, Task
from celery.utils.log import get_task_logger
from time import sleep

log = get_task_logger(__name__)

config = configparser.ConfigParser()
# Set up default options, in case they are missing from the file
config['Tasks'] = {'workdir': '/tmp/tamsat-alert',
                   'days_to_keep_completed': '7',
                   'days_to_keep_downloaded': '1'}
config['Email'] = {'server': 'smtp.reading.ac.uk',
                   'reply-to': 'tamsat@reading.ac.uk',
                   'username': 'CHANGEME',
                   'password': 'CHANGEME'}
config['Celery'] = {'backend': 'redis://',
                    'broker': 'amqp://guest@queue//'}


# Read the config file.  This will overwrite any defaults
config.read('tamsat-alert.cfg')

# Setup the working directory and create if necessary
workdir = config['Tasks']['workdir']
if(os.path.exists(workdir)):
    if(not os.path.isdir(workdir)):
        raise ValueError('The configured working directory ('+workdir+') exists, but it is a file')
else:
    os.mkdir(workdir)

# Setup the celery app
celery_app = Celery('tasks',
                    backend=config['Celery']['backend'],
                    broker=config['Celery']['broker'])

# This is necessary if we want the task to accept non-JSON compatible args
celery_app.conf.update(task_serializer='pickle', accept_content=['json','pickle'])


@celery_app.task()
def tamsat_alert_run(init_date, run_start, run_end, poi_start, poi_end, fc_start, fc_end, stat_type, tercile_weights):
    log.debug('Calling task')
    args = [init_date, run_start, run_end, poi_start, poi_end, fc_start, fc_end, stat_type, tercile_weights]

    # For now, just print out the relevant values
    for i in args:
        print (i, type(i))

    # Setup an output directory in workdir
    output_path = '123ABC'

    # Generate the job ID from the parameters

    # Run the job.  This will run the tamsat alert system, and write data to the
    # output directory
    ta.tamsat_alert_cumrain("all_hist.txt", 0, 1970, 2011, init_date.year, init_date.month, init_date.day, run_start.year, run_start.month, run_start.day, run_end.year, run_end.month, run_end.day, 1970, 2009, 1, "histmetric.txt", "forecastmetric.txt", "ensemble.txt", poi_start.month, poi_start.day, poi_end.month, poi_end.day, poi_start.year, poi_end.year, 3, True, fc_start.month, fc_start.day, fc_end.month, fc_end.day, stat_type, "Title of plot", [tercile_weights[0], tercile_weights[1], tercile_weights[2]])

    return output_path
