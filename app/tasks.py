import configparser
import os
import logging
from tamsat_alert import tamsat_alert as ta
from tamsat_alert.extract_data import extract_point_timeseries
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
config['Data'] = {'path': '/configure/path/to/data',
                  'climatology_start_year': '1983',
                  'climatology_end_year': '2010',
                  'period_of_interest_start_year': '1983',
                  'period_of_interest_end_year': '2010'
                  }
config['Celery'] = {'backend': 'redis://',
                    'broker': 'amqp://guest@queue//'}


# Read the config file.  This will overwrite any defaults
config.read('tamsat-alert.cfg')

# Setup the working directory and create if necessary
workdir = config['Tasks']['workdir']
if(os.path.exists(workdir)):
    if(not os.path.isdir(workdir)):
        raise ValueError('The configured working directory (' +
                         workdir + ') exists, but it is a file')
else:
    os.mkdir(workdir)

# Check that the co

# Setup the celery app
celery_app = Celery('tasks',
                    backend=config['Celery']['backend'],
                    broker=config['Celery']['broker'])

# This is necessary if we want the task to accept non-JSON compatible args
celery_app.conf.update(task_serializer='pickle',
                       accept_content=['json', 'pickle'])


@celery_app.task()
def tamsat_alert_run(location, init_date, poi_start, poi_end, fc_start, fc_end, stat_type, tercile_weights):
    log.debug('Calling task')

    # Setup an output directory in workdir
    output_path = '123ABC'
    plot_title = 'Title of plot'

    # Generate the job ID from the parameters

    # Run the job.  This will run the tamsat alert system, and write data to the
    # output directory
    # Extract a DataFrame containing the data at the specified location

    lon, lat = location
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
    # TODO return path to the zip file?
    # TODO create a temporary output dir, pass it to risk_prob_plot, zip everything
    # based on an input parameter, then return that path?

    return output_path
