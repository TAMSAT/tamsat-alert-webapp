#!/usr/bin/env python3

import os, os.path
from flask import Flask, send_file, abort, request, render_template, jsonify
from threading import Lock, Thread
from math import isclose
from pandas import Timestamp
import pickle
import tasks
from config import config
import exceptions as ex
from datetime import timedelta, datetime as dt


app = Flask(__name__)

lock = Lock()

joblist_filename = 'joblist.dat'


@app.route("/jobs", methods=["GET"])
def get_job_list():
    params = request.args
    # Here, we get the job ref and email from the params
    try:
        email = params['email']
        job_ref = params['ref']
    except KeyError as e:
        # Either the email or ref parameter is missing
        # TODO handle errors properly
        raise ex.InvalidUsage('You must provide a value for '+e.args[0])

    try:
        task_list = submitted_jobs[(email, job_ref)]
    except KeyError:
        # No jobs by that user/ref combination
        task_list = []

    # TODO This template should use the task objects to check whether jobs
    # are completed or not.  If so, link to downloadResult, with a job ID.
    # The job ID is the output path returned by the task.

    return render_template('job_list.html', jobs=task_list)


@app.route("/downloadResult", methods=["GET"])
def download():
    params = request.args

    try:
        job_id = params['job_id']
    except KeyError:
        raise ex.InvalidUsage('You must provide a value for '+e.args[0])

    zipfile = tasks.get_zipfile_from_job_id(job_id)

    if not os.path.exists(zipfile):
        raise ex.InvalidUsage('The job with ID '+job_id+' does not exist on this server.  Completed jobs get removed '+config['Tasks']['days_to_keep_completed']+' days after completion.')

    return send_file(zipfile, attachment_filename='tamsat_alert.zip')


@app.route("/tamsatAlertTask", methods=["POST"])
def submit():
    # Get the POST parameters
    params = request.form

    # Now parse parameters to their correct types and do basic sanity checks
    try:
        locType = params['locationType']
        if(locType.lower() == 'point'):
            location = (float(params['lon']), float(params['lat']))
        elif(locType.lower() == 'region'):
            location = (float(params['minLat']),
                        float(params['maxLat']),
                        float(params['minLon']),
                        float(params['maxLon']))
        else:
            raise ex.InvalidUsage('Parameter "locationType" must be either "point" or "region"')

        init_date = Timestamp(params['initDate'])
        poi_start = Timestamp(params['poiStart'])
        poi_end = Timestamp(params['poiEnd'])
        fc_start = Timestamp(params['forecastStart'])
        fc_end = Timestamp(params['forecastEnd'])

        metric = params['metric']
        if(metric.lower() != 'cumrain' and
                metric.lower() != 'wrsi' and
                metric.lower() != 'soilmoisture'):
            raise ex.InvalidUsage('Parameter "metric" must be one of "cumRain", "wrsi", and "soilMoisture"')

        tl = float(params['tercileLow'])
        tm = float(params['tercileMid'])
        th = float(params['tercileHigh'])
        # Use the isclose method here with a low tolerence
        # This is so that e.g. (0.333,0.333,0.333) still works
        if(not isclose(tl+tm+th, 1.0, abs_tol=1e-3) ):
            raise ex.InvalidUsage('Tercile parameters must add up to 1')
        tercile_weights = (tl, tm, th)

        stat_type = params['stat']

        email = params['email']
        job_ref = params['ref']

    except KeyError as e:
        raise ex.InvalidUsage('You must provide a value for '+e.args[0])

    # Submit to the celery queue
    # TODO either allow different tasks based on "metric", or have one task that chooses correct metric
    task = tasks.tamsat_alert_run.delay(location, init_date, poi_start, poi_end, fc_start, fc_end, stat_type, tercile_weights, email)

    if((email, job_ref) not in submitted_jobs):
        submitted_jobs[(email, job_ref)] = []

    # TODO - anything else to add here?
    # Yes - any details we want to display to the user
    # This will include location and submit time
    submitted_jobs[(email,job_ref)].append(task)

    _save_joblist(tasks.workdir, submitted_jobs)

    # Return job submitted page
    return render_template('job_submitted.html', job_ref = job_ref, email = email)


def _read_joblist(workdir):
    try:
        with open(os.path.join(workdir, joblist_filename), 'rb') as file:
            return pickle.load(file)
    except FileNotFoundError:
        # There is no list of jobs, return an empty dictionary
        return {}


# Initialise the joblist when run
submitted_jobs = _read_joblist(tasks.workdir)


def _save_joblist(workdir, jobs):
    # Start a new thread to save the job list.
    # This uses the file lock, so we don't get 2 simultaneous tasks writing
    # the list to file.  So it may block, hence the new thread
    save_thread = Thread(target = __do_save__, args=(workdir, jobs))
    save_thread.start()


def __do_save__(workdir, jobs):
    # TODO Test this job removal better
    # Factor it out and write some unit tests...
    days = int(config['Tasks']['days_to_keep_completed'])
    for key in jobs:
        joblist = jobs[key]
        jobs[key] = [job for job in joblist
                     if not job.ready() or
                        job.result[tasks.COMPLETED_TIME_KEY] + timedelta(days=days) > dt.now()]


    # Save the submitted jobs list to file here
    # We lock this, so that we don't get inconsistencies
    lock.acquire()

    with open(os.path.join(workdir, joblist_filename), 'wb') as file:
        pickle.dump(jobs, file)

    lock.release()


@app.route("/")
@app.route("/tamsatAlertTask", methods=["GET"])
def main():
    index_path = os.path.join(app.static_folder, 'index.html')
    return send_file(index_path)


# Everything not declared before (not a Flask route / API endpoint)...
@app.route('/<path:path>')
def route_frontend(path):
    # ...could be a static file needed by the front end that
    # doesn't use the `static` path (like in `<script src="bundle.js">`)
    file_path = os.path.join(app.static_folder, path)
    if os.path.isfile(file_path):
        return send_file(file_path)
    # Otherwise, send 404
    else:
        abort(404)

@app.errorhandler(ex.InvalidUsage)
def handle_invalid_usage(error):
    # TODO return a template with the error here
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

if __name__ == "__main__":
    # Only for debugging while developing
    app.run(host='0.0.0.0', debug=True, port=8080)
