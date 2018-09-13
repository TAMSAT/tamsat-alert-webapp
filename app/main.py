#!/usr/bin/env python3

import os, os.path
from flask import Flask, send_file, abort, request, render_template, jsonify
from threading import Lock, Thread
from math import isclose
from pandas import Timestamp
import pickle
import tasks
import util
from config import config
import exceptions as ex
from datetime import timedelta, datetime as dt
import sqlite3
import hashlib


# Define the Flask app at top module level.
# This is the recommended method for small webapps
app = Flask(__name__)



# Setup the working directory and create if necessary
workdir = config['Tasks']['workdir']
if(os.path.exists(workdir)):
    if(not os.path.isdir(workdir)):
        raise ValueError('The configured working directory (' +
                         workdir + ') exists, but it is not a directory')
else:
    os.mkdir(workdir)

# Setup the job list database on first run, if necessary
# No try / except - if this raises an exception, the entire app will fail to start
# That is the desired behaviour - if we can't create the database, something is wrong
db = sqlite3.connect(config['Tasks']['dbfile'])
# 'with' takes care of the commit, but doesn't close the DB
with db:
    c = db.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY AUTOINCREMENT,
            userhash TEXT,
            status TEXT,
            time INTEGER,
            description TEXT,
            job_id TEXT)
    ''')
db.close()


@app.route("/jobs", methods=["GET"])
def get_job_list():
    params = request.args
    # Here, we get the job ref and email from the params
    try:
        email = params['email']
        job_ref = params['ref']
    except KeyError as e:
        # Either the email or ref parameter is missing
        raise ex.InvalidUsage('You must provide a value for '+e.args[0])

    db = sqlite3.connect(config['Tasks']['dbfile'])
    # 'with' takes care of the commit, but doesn't close the DB
    with db:
        db.row_factory = sqlite3.Row
        c = db.cursor()
        c.execute('''
            SELECT description, status, time, job_id
            FROM jobs
            WHERE userhash=?
            ''',
            (_get_hash(email, job_ref),))
        rows = c.fetchall()
    db.close()

    jobs = []
    for row in rows:
        jobs.append({
            'description': row['description'],
            'status': row['status'],
            'time': dt.fromtimestamp(int(row['time'])),
            'job_id': row['job_id']
        })

    return render_template('job_list.html',
        email=email,
        job_ref=job_ref,
        jobs=jobs,
        days_after_completed = config['Tasks']['days_to_keep_completed'],
        hours_after_downloaded = config['Tasks']['hours_to_keep_downloaded'])


@app.route("/downloadResult", methods=["GET"])
def download():
    params = request.args

    try:
        job_id = params['job_id']
    except KeyError:
        raise ex.InvalidUsage('You must provide a value for '+e.args[0])

    zipfile = util.get_zipfile_from_job_id(job_id)

    if not os.path.exists(zipfile) or not os.path.isfile(zipfile):
        raise ex.InvalidUsage('The job with ID '+job_id+' does not exist on this server.  Completed jobs get removed '+config['Tasks']['days_to_keep_completed']+' days after completion.')

    db = sqlite3.connect(config['Tasks']['dbfile'])
    with db:
        c = db.cursor()
        c.execute('''
            UPDATE jobs SET status=?, time=?
            WHERE job_id=?
            ''',
            ('DOWNLOADED', int(dt.now().timestamp()), job_id))
    db.close()

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


    # TODO make descriptive
    description = 'Cumulative rainfall at ' + util.location_to_str(*location)
    db = sqlite3.connect(config['Tasks']['dbfile'])
    # 'with' takes care of the commit, but doesn't close the DB
    with db:
        c = db.cursor()
        c.execute('''
            INSERT INTO jobs(userhash, status, time, description) VALUES(?,?,?,?)
            ''',
            (_get_hash(email, job_ref), 'QUEUED', int(dt.now().timestamp()), description))
        db_key = c.lastrowid
    db.close()

    # Submit to the celery queue
    # TODO Other metrics need implementing (i.e. soil moisture, WRSI)
    task = tasks.tamsat_alert_run.delay(location,
                                        init_date,
                                        poi_start,
                                        poi_end,
                                        fc_start,
                                        fc_end,
                                        stat_type,
                                        tercile_weights,
                                        email,
                                        db_key)


    # Return job submitted page
    return render_template('job_submitted.html',
        job_ref = job_ref,
        email = email,
        days_after_completed = config['Tasks']['days_to_keep_completed'],
        hours_after_downloaded = config['Tasks']['hours_to_keep_downloaded'])


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
    return render_template('error.html',
        message = error.message,
        email = config['Email']['contact'])

def _get_hash(email, job_ref):
    return hashlib.md5((email+job_ref).encode('utf-8')).hexdigest()

if __name__ == "__main__":
    # Only for debugging while developing
    app.run(host='0.0.0.0', debug=True, port=8080)
