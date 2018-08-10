#!/usr/bin/env python3

import os
from flask import Flask, send_file, abort, request, render_template
from threading import Lock, Thread
from datetime import date, datetime
from math import isclose
import tasks

app = Flask(__name__)

lock = Lock()


@app.route("/jobs", methods=["GET"])
def get_job_list():
    params = request.args
    # Here, we get the job ref and email from the params
    email = params['email']
    job_ref = params['ref']
    task_list = submitted_jobs[(email, job_ref)]

    # TODO This template should use the task objects to check whether jobs
    # are completed or not.  If so, link to downloadResult, with a job ID.
    # The job ID is the output path returned by the task.

    return render_template('job_list.html', tasks=tasks)


@app.route("/downloadResult", methods=["GET"]):
    params = request.args

    # The job_id is the output directory containing the data, as returned from the task
    job_id = params['job_id']

    # TODO read whatever the data in that directory is (TBD), and return in in some way
    return


@app.route("/tamsatAlertTask", methods=["POST"])
def submit():
    # Get the POST parameters
    params = request.form

    # Now parse parameters to their correct types and do basic sanity checks (? - form will have sanity checks on input in the JS)
    try:
        # TODO This is currently not used - we need the data extraction module first
        locType = params['locationType']
        if(locType.lower() == 'point'):
            location = (float(params['lat']), float(params['lon']))
        elif(locType.lower() == 'region'):
            location = (float(params['minLat']),
                        float(params['maxLat']),
                        float(params['minLon']),
                        float(params['maxLon']))
        else:
            raise ValueError('Parameter "locationType" must be either "point" or "region"')

        init_date = datetime.strptime(params['initDate'], '%Y-%m-%d').date()
        run_start = datetime.strptime(params['runStart'], '%Y-%m-%d').date()
        run_end = datetime.strptime(params['runEnd'], '%Y-%m-%d').date()
        poi_start = datetime.strptime(params['poiStart'], '%Y-%m-%d').date()
        poi_end = datetime.strptime(params['poiEnd'], '%Y-%m-%d').date()
        fc_start = datetime.strptime(params['forecastStart'], '%Y-%m-%d').date()
        fc_end = datetime.strptime(params['forecastEnd'], '%Y-%m-%d').date()

        metric = params['metric']
        if(metric.lower() != 'cumrain' and
                metric.lower() != 'wrsi' and
                metric.lower() != 'soilmoisture'):
            raise ValueError('Parameter "metric" must be one of "cumRain", "wrsi", and "soilMoisture"')

        tl = float(params['tercileLow'])
        tm = float(params['tercileMid'])
        th = float(params['tercileHigh'])
        # Use the isclose method here with a low tolerence
        # This is so that e.g. (0.333,0.333,0.333) still works
        if(not isclose(tl+tm+th, 1.0, abs_tol=1e-3) ):
            raise ValueError('Tercile parameters must add up to 1')
        tercile_weights = (tl, tm, th)

        stat_type = params['stat']

        email = params['email']
        job_ref = params['ref']

    except Exception as e:
        # TODO handle error with parameters (return an error template, with message)
        # TODO separate KeyError catch clause
        raise Exception('Problem', e)

    # Submit to the celery queue
    # TODO use location parameters to extract data (in tasks.py)
    # TODO either allow different tasks based on "metric", or have one task that chooses correct metric
    task = tasks.tamsat_alert_run.delay(init_date, run_start, run_end, poi_start, poi_end, fc_start, fc_end, stat_type, tercile_weights)

    if((email, job_ref) not in submitted_jobs):
        submitted_jobs[(email, job_ref)] = []

    # TODO - anything else to add here?
    submitted_jobs[(email,job_ref)].append(task)

    # Start a new thread to save the job list.
    # This uses the file lock, so we don't get 2 simultaneous tasks writing
    # the list to file.  So it may block, hence the new thread
    save_thread = Thread(target = _save_joblist, args=(tasks.workdir))
    save_thread.start()

    # Return job submitted page
    return render_template('job_submitted.html', job_ref = job_ref, email = email)


def _read_joblist(workdir):
    # Read the submitted jobs list from file here
    return {}


# Initialise the joblist when run
submitted_jobs = _read_joblist(tasks.workdir)


def _save_joblist(workdir):
    # Save the submitted jobs list to file here
    # We lock this, so that we don't get inconsistencies
    lock.acquire()

    # TODO Check jobs to see if any need to be removed from the list
    # this will happen x days after the task was completed

    # TODO Do save

    lock.release()


@app.route("/")
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


if __name__ == "__main__":
    # Only for debugging while developing
    app.run(host='0.0.0.0', debug=True, port=8080)
